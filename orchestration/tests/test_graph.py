import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration.graph import run_query


def test_nearest_pfz_graph(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = run_query("Where is the nearest fishing zone?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "nearest_pfz"


def test_safe_to_sail_graph(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = run_query("Is it safe to sail tomorrow near Chennai?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "safe_to_sail"


def test_weather_tide_graph(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = run_query("What's the tide near Kochi?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "weather_tide"


def test_geofence_check_graph(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = run_query("Am I close to the maritime boundary?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "geofence_check"
