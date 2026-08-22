from orchestration.state import TurnState, AgentOutput, TraceEntry
from datetime import datetime


def run(state: TurnState) -> TurnState:
    """STUB — Role 4 replaces this with real IMBL/EEZ geofencing logic."""
    state.agent_outputs["geospatial_agent"] = AgentOutput(
        data={"distance_to_boundary_nm": 0, "note": "mock data"},
        source="MOCK",
        timestamp=datetime.utcnow().isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="geospatial_agent",
            action="computed mock geofence distance",
            input_summary=state.resolved_query,
            output_summary="mock boundary distance",
            timestamp=datetime.utcnow().isoformat(),
        )
    )
    return state
