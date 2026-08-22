from orchestration.state import TurnState, AgentOutput
from datetime import datetime


def run(state: TurnState) -> TurnState:
    """STUB — Role 2 replaces this with real INCOIS/IMD data fetching."""
    state.agent_outputs["weather_agent"] = AgentOutput(
        data={"wind_speed_kmh": 0, "wave_height_m": 0, "note": "mock data"},
        source="MOCK",
        timestamp=datetime.utcnow().isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="weather_agent",
            action="fetched mock weather data",
            input_summary=state.resolved_query,
            output_summary="mock wind/wave data",
            timestamp=datetime.utcnow().isoformat(),
        )
    )
    return state
