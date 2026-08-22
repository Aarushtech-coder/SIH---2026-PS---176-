from orchestration.state import TurnState, AgentOutput, TraceEntry
from datetime import datetime


def run(state: TurnState) -> TurnState:
    """STUB — Role 2 replaces this with real INCOIS PFZ data fetching."""
    state.agent_outputs["marine_data_agent"] = AgentOutput(
        data={"pfz_zones": [], "note": "mock data"},
        source="MOCK",
        timestamp=datetime.utcnow().isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="marine_data_agent",
            action="fetched mock PFZ data",
            input_summary=state.resolved_query,
            output_summary="mock PFZ zones",
            timestamp=datetime.utcnow().isoformat(),
        )
    )
    return state
