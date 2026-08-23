from datetime import datetime, timezone

from orchestration.state import AgentOutput, TraceEntry, TurnState


def run(state: TurnState) -> TurnState:
    """STUB — Role 2 replaces this with real INCOIS/IMD data fetching."""
    state.agent_outputs["weather_agent"] = AgentOutput(
        data={"wind_speed_kmh": 0, "wave_height_m": 0, "note": "mock data"},
        source="MOCK",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="weather_agent",
            action="fetched mock weather data",
            input_summary=state.resolved_query,
            output_summary="mock wind/wave data",
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    return state
