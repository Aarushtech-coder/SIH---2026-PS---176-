from datetime import datetime, timezone

from orchestration.state import AgentOutput, TraceEntry, TurnState


def run(state: TurnState) -> TurnState:
    """STUB — Role 2 replaces this with real INCOIS PFZ data fetching."""
    state.agent_outputs["marine_data_agent"] = AgentOutput(
        data={"pfz_zones": [], "note": "mock data"},
        source="MOCK",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="marine_data_agent",
            action="fetched mock PFZ data",
            input_summary=state.resolved_query,
            output_summary="mock PFZ zones",
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    return state
