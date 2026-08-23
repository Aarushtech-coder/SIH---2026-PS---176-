from datetime import datetime, timezone
import json
import os

from dotenv import load_dotenv

from orchestration.state import TraceEntry, TurnState


load_dotenv()


INTENTS = {
    "nearest_pfz",
    "safe_to_sail",
    "weather_tide",
    "geofence_check",
    "general_ocean_info",
    "out_of_scope",
}

AGENTS_BY_INTENT = {
    "nearest_pfz": ["marine_data_agent", "geospatial_agent"],
    "safe_to_sail": ["weather_agent", "ocean_analytics_agent", "risk_agent"],
    "weather_tide": ["weather_agent"],
    "geofence_check": ["geospatial_agent", "risk_agent"],
    # No specialist agents needed for these two; synthesizer handles them directly.
    "general_ocean_info": [],
    "out_of_scope": [],
}

# Words that indicate at least some marine / ocean relevance.
_MARINE_KEYWORDS = {
    "sea",
    "ocean",
    "fish",
    "sail",
    "tide",
    "wave",
    "boat",
    "coast",
    "marine",
    "weather",
    "zone",
    "boundary",
    "pfz",
    "port",
    "harbour",
    "harbor",
    "reef",
    "monsoon",
    "tsunami",
    "current",
    "maritime",
    "fishing",
    "nautical",
    "bay",
    "gulf",
    "lagoon",
    "shore",
    "beach",
    "storm",
    "cyclone",
    "depth",
    "seawater",
    "aquatic",
}

# Follow-up signal phrases used by the keyword fallback in resolve_context().
# Stored as a list (not a set) so multi-word phrases like "what about" and
# "that area" are matched as substrings, not split into individual tokens.
_FOLLOWUP_SIGNALS = [
    "further",
    "there",
    "that area",
    "same place",
    "what about",
    "and the",
    "also",
]


def _classify_with_llm(query_text: str) -> str:
    """Send query_text to Groq for intent classification."""
    api_key = os.environ["GROQ_API_KEY"]

    from groq import Groq

    client = Groq(api_key=api_key, timeout=10.0)
    model_name = "openai/gpt-oss-120b"
    response = client.chat.completions.create(
        model=model_name,
        max_tokens=200,
        temperature=0,
        reasoning_effort="low",
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the user's query into exactly one of these six intents "
                    "and return ONLY the intent string, nothing else.\n\n"
                    "Intents:\n"
                    "- nearest_pfz: user wants to find the nearest Potential Fishing Zone\n"
                    "- safe_to_sail: user asks whether conditions are safe for sailing/fishing\n"
                    "- weather_tide: user asks about weather, sea state, or tidal conditions\n"
                    "- geofence_check: user asks about maritime boundaries or restricted zones\n"
                    "- general_ocean_info: query is genuinely about ocean/marine topics but "
                    "does not match any of the four specific actionable intents above "
                    "(e.g. coral reefs, why fish catch declined, how tsunamis form, "
                    "monsoon fishing patterns)\n"
                    "- out_of_scope: query has no connection to the ocean or marine domain "
                    "(e.g. cricket scores, jokes, Delhi weather, general trivia)"
                ),
            },
            {"role": "user", "content": query_text},
        ],
    )

    content = response.choices[0].message.content.strip().lower()
    for intent in INTENTS:
        if intent in content:
            return intent

    raise ValueError(f"Unexpected planner intent: {content}")


def _classify_with_fallback(query_text: str) -> str:
    """Keyword-based intent classification used when the LLM is unavailable."""
    query = query_text.lower()

    # Keyword checks for the four specific actionable intents.
    if "pfz" in query or "fishing zone" in query:
        return "nearest_pfz"
    if "boundary" in query or "imbl" in query or "border" in query:
        return "geofence_check"
    if "tide" in query or "tidal" in query:
        return "weather_tide"
    if "safe" in query or "sail" in query:
        return "safe_to_sail"
    if "weather" in query and any(
        w in query for w in ("sea", "ocean", "coast", "marine", "wave")
    ):
        return "weather_tide"

    # If no marine-related word appears, treat as out-of-scope.
    query_words = set(query.split())
    if not query_words.intersection(_MARINE_KEYWORDS):
        return "out_of_scope"

    # Fallback for queries that mention ocean topics but don't match a specific
    # actionable intent — general ocean knowledge rather than a safety verdict.
    return "general_ocean_info"


def resolve_context(raw_query: str, previous_turn: TurnState | None) -> dict:
    """
    Decide whether raw_query is a follow-up to previous_turn and, if so,
    rewrite it into a self-contained query that incorporates prior context.

    Returns a dict with keys:
        resolved_query  (str)
        user_location   (dict | None)
        query_date      (str | None)

    This function must never raise — any failure falls back to returning
    raw_query unchanged with no inherited context.
    """
    # --- Path 1: No prior context; nothing to resolve. ---
    if previous_turn is None:
        return {"resolved_query": raw_query, "user_location": None, "query_date": None}

    try:
        # --- LLM path: ask the model to decide follow-up vs. independent. ---
        api_key = os.environ["GROQ_API_KEY"]
        from groq import Groq

        client = Groq(api_key=api_key, timeout=10.0)
        prev_q = previous_turn.resolved_query or previous_turn.raw_query
        prev_loc = previous_turn.user_location

        prompt = (
            "You are a context-resolution assistant. Given a previous query and a new "
            "query, decide whether the new query is a follow-up that depends on the "
            "previous one, or whether it is fully independent.\n\n"
            f'Previous query: "{prev_q}"\n'
            f"Previous location: {json.dumps(prev_loc)}\n"
            f'New query: "{raw_query}"\n\n'
            "Reply ONLY with valid JSON (no markdown, no extra text):\n"
            '{"is_followup": <true|false>, '
            '"resolved_query": "<self-contained rewrite of the new query>", '
            '"inherit_location": <true|false>}'
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=300,
            temperature=0,
            reasoning_effort="low",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if the model wrapped in ```json … ```.
        raw = raw.removeprefix("```json").removeprefix("```").strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        parsed = json.loads(raw.strip())

        resolved_query = parsed.get("resolved_query") or raw_query
        inherit_location = bool(parsed.get("inherit_location", False))
        user_location = prev_loc if inherit_location else None

        return {
            "resolved_query": resolved_query,
            "user_location": user_location,
            "query_date": None,
        }

    except Exception:
        # --- Fallback: keyword heuristic for follow-up detection. ---
        # If recognisable follow-up signal words are present, enrich the query
        # with previous context in plain text so the planner can still classify it.
        query_lower = raw_query.lower()
        is_followup = any(signal in query_lower for signal in _FOLLOWUP_SIGNALS)

        if is_followup:
            prev_q = previous_turn.resolved_query or previous_turn.raw_query
            resolved_query = f"{raw_query} (context: previous query was '{prev_q}')"
            # Inherit the previous turn's location for geographic continuity.
            user_location = previous_turn.user_location
        else:
            resolved_query = raw_query
            user_location = None

        return {
            "resolved_query": resolved_query,
            "user_location": user_location,
            "query_date": None,
        }


def run(state: TurnState) -> TurnState:
    method = "Groq LLM"

    # Use resolved_query for classification if it was already set by resolve_context();
    # otherwise fall back to raw_query. This preserves context-enriched rewrites.
    classify_text = state.resolved_query if state.resolved_query else state.raw_query

    try:
        intent = _classify_with_llm(classify_text)
    except Exception:
        method = "fallback"
        intent = _classify_with_fallback(classify_text)

    required_agents = AGENTS_BY_INTENT[intent]
    state.intent = intent
    state.required_agents = required_agents

    # Only set resolved_query if it hasn't already been populated by resolve_context().
    # Overwriting it here would lose the context-enriched rewrite done before graph
    # execution started.
    if not state.resolved_query:
        state.resolved_query = state.raw_query

    state.trace.append(
        TraceEntry(
            agent="planner",
            action="classify_intent",
            input_summary=classify_text,
            output_summary=(
                f"Used {method}; chose intent '{intent}' and agents {required_agents}."
            ),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    return state
