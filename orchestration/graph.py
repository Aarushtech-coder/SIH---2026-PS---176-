from typing import Any
import uuid

from langgraph.graph import StateGraph

from orchestration import planner, session_store, synthesizer
from orchestration.agents import (
    geospatial_agent,
    marine_data_agent,
    ocean_analytics_agent,
    risk_agent,
    weather_agent,
)
from orchestration.state import TurnState


AGENT_RUNNERS = {
    "weather_agent": weather_agent.run,
    "marine_data_agent": marine_data_agent.run,
    "ocean_analytics_agent": ocean_analytics_agent.run,
    "risk_agent": risk_agent.run,
    "geospatial_agent": geospatial_agent.run,
}


def _state_to_dict(state: TurnState) -> dict[str, Any]:
    if hasattr(state, "model_dump"):
        return state.model_dump()
    return state.dict()


def _dict_to_state(state: dict[str, Any] | TurnState) -> TurnState:
    if isinstance(state, TurnState):
        return state
    if hasattr(TurnState, "model_validate"):
        return TurnState.model_validate(state)
    return TurnState.parse_obj(state)


def _wrap_node(runner):
    def node(state: dict[str, Any]) -> dict[str, Any]:
        turn_state = _dict_to_state(state)
        return _state_to_dict(runner(turn_state))

    return node


def _route_from_planner(state: dict[str, Any]) -> str:
    turn_state = _dict_to_state(state)
    if turn_state.required_agents:
        return turn_state.required_agents[0]
    return "synthesizer"


def _route_after_agent(agent_name: str):
    def route(state: dict[str, Any]) -> str:
        turn_state = _dict_to_state(state)
        try:
            current_index = turn_state.required_agents.index(agent_name)
        except ValueError:
            return "synthesizer"

        next_index = current_index + 1
        if next_index < len(turn_state.required_agents):
            return turn_state.required_agents[next_index]
        return "synthesizer"

    return route


# Use a dict schema for LangGraph and adapt at node boundaries. This keeps the
# graph compatible across LangGraph versions while preserving TurnState inside
# the planner, agent, and synthesizer functions.
graph = StateGraph(dict)
graph.add_node("planner", _wrap_node(planner.run))
graph.add_node("weather_agent", _wrap_node(weather_agent.run))
graph.add_node("marine_data_agent", _wrap_node(marine_data_agent.run))
graph.add_node("ocean_analytics_agent", _wrap_node(ocean_analytics_agent.run))
graph.add_node("risk_agent", _wrap_node(risk_agent.run))
graph.add_node("geospatial_agent", _wrap_node(geospatial_agent.run))
graph.add_node("synthesizer", _wrap_node(synthesizer.run))

graph.set_entry_point("planner")
graph.add_conditional_edges(
    "planner",
    _route_from_planner,
    {
        "weather_agent": "weather_agent",
        "marine_data_agent": "marine_data_agent",
        "ocean_analytics_agent": "ocean_analytics_agent",
        "risk_agent": "risk_agent",
        "geospatial_agent": "geospatial_agent",
        "synthesizer": "synthesizer",
    },
)

for agent in AGENT_RUNNERS:
    graph.add_conditional_edges(
        agent,
        _route_after_agent(agent),
        {
            "weather_agent": "weather_agent",
            "marine_data_agent": "marine_data_agent",
            "ocean_analytics_agent": "ocean_analytics_agent",
            "risk_agent": "risk_agent",
            "geospatial_agent": "geospatial_agent",
            "synthesizer": "synthesizer",
        },
    )

graph.set_finish_point("synthesizer")
app = graph.compile()


def run_query(
    raw_query: str,
    session_id: str = "default",
    turn_id: str | None = None,
    user_location: dict | None = None,
) -> TurnState:
    # Auto-generate a unique turn_id if not supplied.
    if turn_id is None:
        turn_id = str(uuid.uuid4())

    # Retrieve the previous turn from the session store for context resolution.
    previous_turn = session_store.get_previous_turn(session_id)

    # Ask the planner to rewrite the query using prior context when relevant.
    context = planner.resolve_context(raw_query, previous_turn)

    # GPS priority: an explicitly-passed user_location (fresh device reading)
    # always overrides whatever resolve_context() may have inherited from a
    # previous turn. Fall back to the inherited context value when None.
    resolved_location = (
        user_location if user_location is not None else context.get("user_location")
    )

    # Build the initial TurnState with context-resolved values pre-filled so the
    # planner node inside the graph sees them and will not overwrite resolved_query.
    state = TurnState(
        turn_id=turn_id,
        raw_query=raw_query,
        resolved_query=context["resolved_query"],
        user_location=resolved_location,
        query_date=context.get("query_date"),
    )

    # Run the full Planner → Agents → Synthesizer graph.
    result_dict = app.invoke(_state_to_dict(state))
    result = _dict_to_state(result_dict)

    # Persist the completed turn to the session store before returning.
    session_store.add_turn(session_id, result)

    return result
