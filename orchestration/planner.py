import json
import os
from datetime import datetime, timezone

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
    "weather_tide": ["weather_agent", "ocean_analytics_agent"],
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


def _geocode_location(location_name: str) -> dict | None:
    """Hit OSM Nominatim to convert location name to lat/lon."""
    import urllib.request
    import urllib.parse
    import json

    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(location_name)}&format=json&limit=1&addressdetails=0"
    req = urllib.request.Request(url, headers={"User-Agent": "ORCA-PlannerAgent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data:
                    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                    return {"lat": lat, "lon": lon}
    except Exception:
        pass
    return None


def _detect_language_from_unicode(text: str) -> str:
    """
    Guess the dominant script/language from Unicode code-point ranges.
    Returns an ISO 639-1 code. Defaults to 'en' for Latin-only text.
    """
    script_counts: dict[str, int] = {
        "hi": 0,  # Devanagari  U+0900–U+097F
        "ta": 0,  # Tamil       U+0B80–U+0BFF
        "te": 0,  # Telugu      U+0C00–U+0C7F
        "bn": 0,  # Bengali     U+0980–U+09FF
        "pa": 0,  # Gurmukhi    U+0A00–U+0A7F
        "ur": 0,  # Arabic      U+0600–U+06FF
    }
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            script_counts["hi"] += 1
        elif 0x0B80 <= cp <= 0x0BFF:
            script_counts["ta"] += 1
        elif 0x0C00 <= cp <= 0x0C7F:
            script_counts["te"] += 1
        elif 0x0980 <= cp <= 0x09FF:
            script_counts["bn"] += 1
        elif 0x0A00 <= cp <= 0x0A7F:
            script_counts["pa"] += 1
        elif 0x0600 <= cp <= 0x06FF:
            script_counts["ur"] += 1

    best_lang, best_count = "en", 0
    for lang, count in script_counts.items():
        if count > best_count:
            best_lang, best_count = lang, count
    return best_lang


def _classify_with_llm(query_text: str) -> tuple[str, str, str | None]:
    """
    Send query_text to Groq for intent classification AND language detection.
    Returns (intent, language, location_name) where language is an ISO 639-1 code.
    """
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
                    "Classify the user's query into exactly one of these six intents, "
                    "detect the language of the raw query text, AND extract any specific "
                    "location mentioned (city, region, place).\n\n"
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
                    "(e.g. cricket scores, jokes, Delhi weather, general trivia)\n\n"
                    "For language detection: identify the language of the user's raw query "
                    'text itself (e.g. a Hindi query → "hi", Tamil → "ta", '
                    'English → "en"). Use ISO 639-1 two-letter codes.\n\n'
                    "Return ONLY strict JSON with no markdown, no extra text:\n"
                    '{"intent": "<one of the six intents>", "language": "<ISO 639-1 code>", "location_name": "<extracted location name or null if none>"}'
                ),
            },
            {"role": "user", "content": query_text},
        ],
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if the model wrapped in ```json … ```.
    raw = raw.removeprefix("```json").removeprefix("```").strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()

    parsed = json.loads(raw)

    # Robustly extract intent using the same "contains one of six valid values" check.
    raw_intent = str(parsed.get("intent", "")).strip().lower()
    intent = None
    for candidate in INTENTS:
        if candidate in raw_intent:
            intent = candidate
            break
    if intent is None:
        raise ValueError(f"Unexpected planner intent in JSON: {raw_intent}")

    # Robustly extract language; default to "en" if missing/invalid/not 2 letters.
    raw_lang = str(parsed.get("language", "")).strip().lower()
    language = raw_lang if (len(raw_lang) == 2 and raw_lang.isalpha()) else "en"

    location_name = parsed.get("location_name")
    if (
        not isinstance(location_name, str)
        or not location_name.strip()
        or location_name.lower() == "null"
    ):
        location_name = None

    return intent, language, location_name


def _classify_with_fallback(query_text: str) -> tuple[str, str, str | None]:
    """
    Keyword-based intent classification used when the LLM is unavailable.
    Also guesses the query language via Unicode character ranges.
    Returns (intent, language, location_name).
    """
    query = query_text.lower()

    # --- Intent detection (unchanged logic) ---
    if "pfz" in query or "fishing zone" in query:
        intent = "nearest_pfz"
    elif "boundary" in query or "imbl" in query or "border" in query:
        intent = "geofence_check"
    elif "tide" in query or "tidal" in query:
        intent = "weather_tide"
    elif "safe" in query or "sail" in query:
        intent = "safe_to_sail"
    elif "weather" in query and any(
        w in query for w in ("sea", "ocean", "coast", "marine", "wave")
    ):
        intent = "weather_tide"
    else:
        # If no marine-related word appears, treat as out-of-scope.
        query_words = set(query.split())
        if not query_words.intersection(_MARINE_KEYWORDS):
            intent = "out_of_scope"
        else:
            # Fallback for queries that mention ocean topics but don't match a specific
            # actionable intent — general ocean knowledge rather than a safety verdict.
            intent = "general_ocean_info"

    # --- Language detection via Unicode script ranges ---
    language = _detect_language_from_unicode(query_text)

    return intent, language, None


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
        intent, language, location_name = _classify_with_llm(classify_text)
    except Exception:
        method = "fallback"
        intent, language, location_name = _classify_with_fallback(classify_text)

    # If the user asked about a specific location, geocode it and override default
    if location_name:
        geocoded = _geocode_location(location_name)
        if geocoded:
            state.user_location = geocoded

    required_agents = AGENTS_BY_INTENT[intent]
    state.intent = intent
    state.language = language
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
                f"Used {method}; chose intent '{intent}', language '{language}', "
                f"and agents {required_agents}."
            ),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    return state
