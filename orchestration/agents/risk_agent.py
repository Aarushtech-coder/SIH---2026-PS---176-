from datetime import datetime, timezone

from orchestration.state import AgentOutput, TraceEntry, TurnState


def run(state: TurnState) -> TurnState:
    """STUB — Role 3 replaces this with real IMD/INCOIS threshold-based risk logic."""
    state.agent_outputs["risk_agent"] = AgentOutput(
        data={"verdict": "unknown", "thresholds_used": {}, "note": "mock data"},
        source="MOCK",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="risk_agent",
            action="computed mock risk verdict",
            input_summary=state.resolved_query,
            output_summary="mock verdict",
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    return state
