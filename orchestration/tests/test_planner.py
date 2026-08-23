import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration import planner
from orchestration.state import TurnState


def _state(query: str) -> TurnState:
    return TurnState(turn_id="test-turn", raw_query=query)


def test_nearest_pfz_uses_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = planner.run(_state("Where is the nearest fishing zone?"))

    assert state.intent == "nearest_pfz"
    assert state.required_agents == ["marine_data_agent", "geospatial_agent"]


def test_safe_to_sail_uses_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = planner.run(_state("Is it safe to sail tomorrow?"))

    assert state.intent == "safe_to_sail"
    assert state.required_agents == [
        "weather_agent",
        "ocean_analytics_agent",
        "risk_agent",
    ]


def test_weather_tide_uses_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = planner.run(_state("What's the tide near Chennai?"))

    assert state.intent == "weather_tide"
    assert state.required_agents == ["weather_agent"]


def test_geofence_check_uses_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = planner.run(_state("Am I close to the maritime boundary?"))

    assert state.intent == "geofence_check"
    assert state.required_agents == ["geospatial_agent", "risk_agent"]
