"""
In-memory session store for ORCA multi-turn conversation memory.

IMPORTANT: This store lives in process memory only — it resets on every
server restart (including when uvicorn --reload triggers a reload). This is
intentional and sufficient for a hackathon demo. For production use, replace
with a persistent backend (Redis, DB, etc.).
"""

from orchestration.state import Session, TurnState

# Module-level dict mapping session_id -> Session object.
_sessions: dict[str, Session] = {}


def get_or_create_session(session_id: str) -> Session:
    """Return the existing Session for session_id, or create a blank one."""
    if session_id not in _sessions:
        _sessions[session_id] = Session(session_id=session_id)
    return _sessions[session_id]


def get_previous_turn(session_id: str) -> TurnState | None:
    """Return the most recent TurnState in this session, or None if none exist."""
    session = _sessions.get(session_id)
    if session and session.turns:
        return session.turns[-1]
    return None


def add_turn(session_id: str, turn: TurnState) -> None:
    """Append a completed TurnState to the session's turn history."""
    session = get_or_create_session(session_id)
    session.turns.append(turn)
