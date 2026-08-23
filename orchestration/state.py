from pydantic import BaseModel
from typing import Optional, Any


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
    user_location: Optional[dict] = None
    query_date: Optional[str] = None

    intent: str = ""
    required_agents: list[str] = []

    agent_outputs: dict[str, Optional[AgentOutput]] = {
        "weather_agent": None,
        "marine_data_agent": None,
        "ocean_analytics_agent": None,
        "risk_agent": None,
        "geospatial_agent": None,
    }

    trace: list[TraceEntry] = []

    final_answer: Optional[str] = None
    citations: list[str] = []
    disclaimer: Optional[str] = None
    map_data: Optional[dict] = None


class Session(BaseModel):
    session_id: str
    language: str = "en"
    turns: list[TurnState] = []
