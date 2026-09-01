"""
Tests for session-based multi-turn conversation memory.

All tests use monkeypatch.delenv("GROQ_API_KEY") to disable the LLM path,
forcing the keyword-based fallback. No live API key is required.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import orchestration.session_store as store
from orchestration import planner
from orchestration.graph import run_query
from orchestration.state import TurnState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_turn(raw_query: str = "test query", resolved_query: str = "") -> TurnState:
    return TurnState(
        turn_id="t-stub",
        raw_query=raw_query,
        resolved_query=resolved_query,
    )


def _unique_sid(base: str) -> str:
    """Return a unique session_id so tests never share state."""
    import uuid

    return f"{base}-{uuid.uuid4()}"


# ---------------------------------------------------------------------------
# Test 1: Fresh session — get_previous_turn returns None, resolve_context
#         returns raw_query unchanged.
# ---------------------------------------------------------------------------


def test_fresh_session_no_previous_turn(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    sid = _unique_sid("fresh")
    # Brand-new session_id should have no prior turns.
    assert store.get_previous_turn(sid) is None

    # resolve_context with no previous turn must echo raw_query back unchanged.
    result = planner.resolve_context("where is the nearest fishing zone?", None)
    assert result["resolved_query"] == "where is the nearest fishing zone?"
    assert result["user_location"] is None
    assert result["query_date"] is None


# ---------------------------------------------------------------------------
# Test 2: Two sequential run_query calls on the SAME session_id.
#         The session store must reflect each turn after it completes.
# ---------------------------------------------------------------------------


def test_sequential_turns_same_session(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    sid = _unique_sid("seq")

    # Before any call, session has no turns.
    assert store.get_previous_turn(sid) is None

    # First call.
    turn1 = run_query("What is the tide near Kochi?", session_id=sid)
    assert turn1.final_answer

    # After first call, session store must hold exactly one turn.
    prev = store.get_previous_turn(sid)
    assert prev is not None
    assert prev.turn_id == turn1.turn_id
    assert prev.raw_query == "What is the tide near Kochi?"

    # Second call — follow-up phrase to trigger keyword heuristic fallback.
    turn2 = run_query("what about further north?", session_id=sid)
    assert turn2.final_answer

    # After second call, the latest turn should be turn2.
    after2 = store.get_previous_turn(sid)
    assert after2 is not None
    assert after2.turn_id == turn2.turn_id
    # The resolved_query should have been enriched with context from turn1.
    assert "further north" in turn2.resolved_query.lower()


# ---------------------------------------------------------------------------
# Test 3: Two DIFFERENT session_ids stay isolated — a follow-up phrase in
#         session B must NOT pick up session A's context.
# ---------------------------------------------------------------------------


def test_different_sessions_are_isolated(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    sid_a = _unique_sid("iso-a")
    sid_b = _unique_sid("iso-b")

    # Populate session A with one turn.
    run_query("Is it safe to sail near Chennai?", session_id=sid_a)

    # Session B has no prior turns even though A does.
    assert store.get_previous_turn(sid_b) is None

    # A follow-up call in session B should NOT inherit session A's context.
    context_b = planner.resolve_context("what about further north?", None)
    # With previous_turn=None, resolved_query must equal raw_query exactly.
    assert context_b["resolved_query"] == "what about further north?"
    assert context_b["user_location"] is None


# ---------------------------------------------------------------------------
# Test 4: planner.run() must NOT reset resolved_query if it was already set
#         before run() was called (Part 2 Change B).
# ---------------------------------------------------------------------------


def test_planner_run_preserves_resolved_query(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    pre_resolved = "what about fishing zones further north of Kochi? (context: previous query was 'nearest pfz near Kochi')"
    state = TurnState(
        turn_id="t-test",
        raw_query="what about further north?",
        resolved_query=pre_resolved,
    )

    result = planner.run(state)

    # resolved_query must still be the enriched version, not raw_query.
    assert result.resolved_query == pre_resolved
    assert result.resolved_query != result.raw_query
