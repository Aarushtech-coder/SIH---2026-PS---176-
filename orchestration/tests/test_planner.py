import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration import planner
from orchestration.state import TurnState


def _state(query: str) -> TurnState:
    return TurnState(turn_id="test-turn", raw_query=query)


def test_nearest_pfz_uses_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = planner.run(_state("Where is the nearest fishing zone?"))

    assert state.intent == "nearest_pfz"
    assert state.required_agents == ["marine_data_agent", "geospatial_agent"]


def test_safe_to_sail_uses_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = planner.run(_state("Is it safe to sail tomorrow?"))

    assert state.intent == "safe_to_sail"
    assert state.required_agents == [
        "weather_agent",
        "ocean_analytics_agent",
        "risk_agent",
    ]


def test_weather_tide_uses_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = planner.run(_state("What's the tide near Chennai?"))

    assert state.intent == "weather_tide"
    assert state.required_agents == ["weather_agent", "ocean_analytics_agent"]


def test_geofence_check_uses_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = planner.run(_state("Am I close to the maritime boundary?"))

    assert state.intent == "geofence_check"
    assert state.required_agents == ["geospatial_agent"]


def test_general_ocean_info_uses_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    # This is a genuine ocean question that doesn't fit any actionable intent.
    state = planner.run(_state("why did fish catch decline this season?"))

    assert state.intent == "general_ocean_info"
    assert state.required_agents == []


def test_out_of_scope_uses_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    # Completely unrelated to ocean/marine domain.
    state = planner.run(_state("tell me a joke"))

    assert state.intent == "out_of_scope"
    assert state.required_agents == []


def test_out_of_scope_no_marine_words(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = planner.run(_state("who won the cricket match yesterday?"))

    assert state.intent == "out_of_scope"
    assert state.required_agents == []


def test_hindi_query_language_detection_fallback(monkeypatch):
    """Hindi Devanagari query should detect language='hi' via the Unicode-range heuristic."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    # 'Is it safe to go to sea tomorrow?' in Hindi
    state = planner.run(_state("क्या कल समुद्र में जाना सुरक्षित है?"))

    assert state.language == "hi"
