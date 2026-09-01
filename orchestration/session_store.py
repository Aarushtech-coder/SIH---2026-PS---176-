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

import json
from pathlib import Path

_SESSION_CACHE_FILE = Path(__file__).resolve().parent / ".session_cache.json"


def _load_sessions_from_disk() -> None:
    """Best-effort restore of sessions after a server restart. Never raises —
    a missing/corrupt cache file just means starting with empty sessions."""
    if not _SESSION_CACHE_FILE.exists():
        return
    try:
        raw = json.loads(_SESSION_CACHE_FILE.read_text(encoding="utf-8"))
        for session_id, session_dict in raw.items():
            _sessions[session_id] = Session(**session_dict)
    except Exception:
        pass


def _save_sessions_to_disk() -> None:
    """Best-effort persistence. Never raises — a failed write just means the
    next restart loses this session, same as before this feature existed."""
    try:
        serializable = {
            sid: (
                session.model_dump()
                if hasattr(session, "model_dump")
                else session.dict()
            )
            for sid, session in _sessions.items()
        }
        _SESSION_CACHE_FILE.write_text(
            json.dumps(serializable, default=str), encoding="utf-8"
        )
    except Exception:
        pass


_load_sessions_from_disk()


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
    _save_sessions_to_disk()
