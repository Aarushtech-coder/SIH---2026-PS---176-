from orchestration.state import TurnState, AgentOutput, TraceEntry
from datetime import datetime


def run(state: TurnState) -> TurnState:
    """STUB — Role 3 replaces this with real IMD/INCOIS threshold-based risk logic."""
    state.agent_outputs["risk_agent"] = AgentOutput(
        data={"verdict": "unknown", "thresholds_used": {}, "note": "mock data"},
        source="MOCK",
        timestamp=datetime.utcnow().isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="risk_agent",
            action="computed mock risk verdict",
            input_summary=state.resolved_query,
            output_summary="mock verdict",
            timestamp=datetime.utcnow().isoformat(),
        )
    )
    return state
