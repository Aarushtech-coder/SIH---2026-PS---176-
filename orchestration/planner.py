from datetime import datetime
import os

from dotenv import load_dotenv

from orchestration.state import TraceEntry, TurnState


load_dotenv()


INTENTS = {
    "nearest_pfz",
    "safe_to_sail",
    "weather_tide",
    "geofence_check",
}

AGENTS_BY_INTENT = {
    "nearest_pfz": ["marine_data_agent", "geospatial_agent"],
    "safe_to_sail": ["weather_agent", "ocean_analytics_agent", "risk_agent"],
    "weather_tide": ["weather_agent"],
    "geofence_check": ["geospatial_agent", "risk_agent"],
}


def _classify_with_llm(raw_query: str) -> str:
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
                    "Classify the user's marine assistance query into exactly "
                    "one of these intents: nearest_pfz, safe_to_sail, "
                    "weather_tide, geofence_check. Return ONLY the intent "
                    "string and nothing else."
                ),
            },
            {"role": "user", "content": raw_query},
        ],
    )

    content = response.choices[0].message.content.strip().lower()
    for intent in INTENTS:
        if intent in content:
            return intent

    raise ValueError(f"Unexpected planner intent: {content}")


def _classify_with_fallback(raw_query: str) -> str:
    query = raw_query.lower()

    # The LLM is the primary classifier, but the Planner is on the critical
    # path for maritime safety. Keyword fallback keeps the graph usable when
    # credentials, network access, or the API are unavailable.
    if "pfz" in query or "zone" in query or "fishing zone" in query:
        return "nearest_pfz"
    if "boundary" in query or "imbl" in query or "border" in query:
        return "geofence_check"
    if "tide" in query or "weather" in query:
        return "weather_tide"
    if "safe" in query or "sail" in query:
        return "safe_to_sail"

    # Unknown queries default to the highest-stakes route so safety analysis is
    # not silently skipped just because classification was uncertain.
    return "safe_to_sail"


def run(state: TurnState) -> TurnState:
    method = "Groq LLM"

    try:
        intent = _classify_with_llm(state.raw_query)
    except Exception:
        method = "fallback"
        intent = _classify_with_fallback(state.raw_query)

    required_agents = AGENTS_BY_INTENT[intent]
    state.intent = intent
    state.required_agents = required_agents
    state.resolved_query = state.raw_query
    state.trace.append(
        TraceEntry(
            agent="planner",
            action="classify_intent",
            input_summary=state.raw_query,
            output_summary=(
                f"Used {method}; chose intent '{intent}' and agents "
                f"{required_agents}."
            ),
            timestamp=datetime.utcnow().isoformat(),
        )
    )
    return state
