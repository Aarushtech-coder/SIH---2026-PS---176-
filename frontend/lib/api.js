import { SCENARIOS, classifyIntent } from "./mockData";

// Single seam between the UI and the orchestration backend. Every caller
// goes through sendQuery() -- Role 1's orchestration/graph.py run_query()
// is now exposed over HTTP at http://localhost:8000/query, so USE_MOCK is
// off and this function calls the real backend. TurnState shape (state.py)
// stays identical either way.
const USE_MOCK = false;
const API_BASE_URL = "http://localhost:8000";

const ALL_AGENT_NAMES = [
  "weather_agent",
  "marine_data_agent",
  "ocean_analytics_agent",
  "risk_agent",
  "geospatial_agent",
];

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildTurnState(rawQuery, scenario) {
  const now = new Date().toISOString();
  const agent_outputs = Object.fromEntries(
    ALL_AGENT_NAMES.map((name) => [name, null]),
  );
  for (const [name, output] of Object.entries(scenario.agent_outputs)) {
    agent_outputs[name] = output;
  }

  return {
    turn_id: `turn-${Date.now()}`,
    raw_query: rawQuery,
    resolved_query: rawQuery,
    intent: scenario.intent,
    required_agents: scenario.required_agents,
    agent_outputs,
    trace: [],
    final_answer: scenario.final_answer,
    citations: scenario.citations,
    disclaimer: scenario.disclaimer,
    map_data: scenario.map_data,
    generated_at: now,
  };
}

// Calls the real orchestration backend and replays its trace entries with
// small delays, so the reasoning panel still animates step-by-step instead
// of popping in all at once (matches the mock's UX).
async function sendQueryLive(rawQuery, { onTrace, onPlan } = {}) {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: rawQuery }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const message =
      errorBody?.detail?.message ||
      errorBody?.error ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  const turnState = await response.json();

  onPlan?.(["planner", ...(turnState.required_agents || []), "synthesizer"]);

  const fullTrace = turnState.trace || [];
  const replayedTrace = [];
  for (const entry of fullTrace) {
    replayedTrace.push(entry);
    onTrace?.(entry);
    await delay(350);
  }

  return turnState;
}

// Resolves with the final TurnState. Calls onTrace(entry) as each step of
// the multi-agent run completes, so the UI can render the reasoning panel
// live instead of popping in all at once.
export async function sendQuery(rawQuery, { onTrace, onPlan } = {}) {
  if (!USE_MOCK) {
    return sendQueryLive(rawQuery, { onTrace, onPlan });
  }

  const intent = classifyIntent(rawQuery);
  const scenario = SCENARIOS[intent];
  const turnState = buildTurnState(rawQuery, scenario);

  onPlan?.(["planner", ...scenario.required_agents, "synthesizer"]);

  const plannerEntry = {
    agent: "planner",
    action: "classify_intent",
    input_summary: `raw_query="${rawQuery}"`,
    output_summary: `intent=${intent}; required_agents=${scenario.required_agents.join(", ")}`,
    timestamp: new Date().toISOString(),
  };
  turnState.trace.push(plannerEntry);
  onTrace?.(plannerEntry);
  await delay(350);

  for (const step of scenario.trace) {
    const entry = { ...step, timestamp: new Date().toISOString() };
    turnState.trace.push(entry);
    onTrace?.(entry);
    await delay(450);
  }

  const synthesizerEntry = {
    agent: "synthesizer",
    action: "produce_final_answer",
    input_summary: `intent=${intent}; outputs=${scenario.citations.join(", ")}`,
    output_summary: "Produced final answer from mock agent outputs.",
    timestamp: new Date().toISOString(),
  };
  turnState.trace.push(synthesizerEntry);
  onTrace?.(synthesizerEntry);

  return turnState;
}
