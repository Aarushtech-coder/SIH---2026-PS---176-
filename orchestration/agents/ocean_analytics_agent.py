from orchestration.state import TurnState, AgentOutput, TraceEntry
from datetime import datetime


def run(state: TurnState) -> TurnState:
    """STUB — Role 3 replaces this with real SST/chlorophyll data from MOSDAC/Bhuvan."""
    state.agent_outputs["ocean_analytics_agent"] = AgentOutput(
        data={"sst_celsius": 0, "chlorophyll": 0, "note": "mock data"},
        source="MOCK",
        timestamp=datetime.utcnow().isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="ocean_analytics_agent",
            action="fetched mock ocean analytics data",
            input_summary=state.resolved_query,
            output_summary="mock SST/chlorophyll",
            timestamp=datetime.utcnow().isoformat(),
        )
    )
    return state
