import { SCENARIOS, classifyIntent } from "./mockData";

// Single seam between the UI and the orchestration backend. Every caller
// goes through sendQuery() -- once Role 1 exposes orchestration/graph.py's
// run_query() over HTTP, only this function's body needs to change to a
// fetch() call; TurnState shape (state.py) stays identical either way.
const USE_MOCK = true;

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
  const agent_outputs = Object.fromEntries(ALL_AGENT_NAMES.map((name) => [name, null]));
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

// Resolves with the final TurnState. Calls onTrace(entry) as each step of
// the (simulated) multi-agent run completes, so the UI can render the
// reasoning panel live instead of popping in all at once.
export async function sendQuery(rawQuery, { onTrace, onPlan } = {}) {
  if (!USE_MOCK) {
    throw new Error("Live orchestration API not wired up yet -- flip USE_MOCK once it exists.");
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
