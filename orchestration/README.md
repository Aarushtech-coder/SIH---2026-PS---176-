# ORCA — Orchestration Layer

Architecture: Planner Agent → specialist agents (weather, marine_data,
ocean_analytics, risk, geospatial) → Synthesizer, using LangGraph with a
shared TurnState object (see state.py).

Each specialist agent lives in agents/<name>\_agent.py and exposes a single
`run(state: TurnState) -> TurnState` function. Read your section of state.py
before building — that's your input/output contract. Don't change state.py
without syncing with Role 1.
