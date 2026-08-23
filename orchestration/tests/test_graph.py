import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration.graph import run_query


def test_nearest_pfz_graph(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = run_query("Where is the nearest fishing zone?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "nearest_pfz"


def test_safe_to_sail_graph(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = run_query("Is it safe to sail tomorrow near Chennai?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "safe_to_sail"


def test_weather_tide_graph(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = run_query("What's the tide near Kochi?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "weather_tide"


def test_geofence_check_graph(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = run_query("Am I close to the maritime boundary?")

    assert state.final_answer
    assert len(state.trace) > 1
    assert state.intent == "geofence_check"


def test_general_ocean_info_graph(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = run_query("why did fish catch decline this season?")

    # No specialist agents; synthesizer handles it directly.
    assert state.final_answer
    assert state.intent == "general_ocean_info"
    assert state.required_agents == []
    # Only planner + synthesizer trace entries expected (no agent nodes).
    assert len(state.trace) >= 2


def test_out_of_scope_graph(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    state = run_query("tell me a joke")

    assert state.final_answer
    assert state.intent == "out_of_scope"
    assert state.required_agents == []
    # Static message — no agent nodes, just planner + synthesizer.
    assert len(state.trace) >= 2
