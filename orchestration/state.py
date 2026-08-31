from typing import Any

from pydantic import BaseModel


class AgentOutput(BaseModel):
    data: dict[str, Any] = {}
    source: str = ""
    timestamp: str = ""


class TraceEntry(BaseModel):
    agent: str
    action: str
    input_summary: str
    output_summary: str
    timestamp: str


class TurnState(BaseModel):
    turn_id: str
    raw_query: str
    resolved_query: str = ""
    user_location: dict | None = None
    query_date: str | None = None

    intent: str = ""
    language: str = "en"
    required_agents: list[str] = []

    agent_outputs: dict[str, AgentOutput | None] = {
        "weather_agent": None,
        "marine_data_agent": None,
        "ocean_analytics_agent": None,
        "risk_agent": None,
        "geospatial_agent": None,
        "productivity_agent": None,
    }

    trace: list[TraceEntry] = []

    final_answer: str | None = None
    citations: list[str] = []
    disclaimer: str | None = None
    map_data: dict | None = None

    map_data: dict | None = None
    # Optional catch-history observations supplied by the app for
    # productivity_agent's chlorophyll/SST correlation. Each item is a dict
    # like {"catch_kg": float, "chlorophyll_mg_per_m3": float, "sst_celsius": float|None}.
    catch_history: list[dict] | None = None


class Session(BaseModel):
    session_id: str
    language: str = "en"
    turns: list[TurnState] = []
