from datetime import datetime
from typing import Any

from orchestration.state import TraceEntry, TurnState


def _format_value(value: Any) -> str:
    if isinstance(value, dict):
        if not value:
            return "none"
        return ", ".join(f"{key}: {_format_value(val)}" for key, val in value.items())
    if isinstance(value, list):
        if not value:
            return "none"
        return ", ".join(_format_value(item) for item in value)
    return str(value)


def _summarize_outputs(state: TurnState) -> tuple[list[str], list[str]]:
    sections = []
    citations = []

    for agent_name, output in state.agent_outputs.items():
        if output is None:
            continue

        citations.append(agent_name)
        data_summary = _format_value(output.data)
        source = output.source or agent_name
        sections.append(f"{agent_name} ({source}) reports {data_summary}")

    return sections, citations


def run(state: TurnState) -> TurnState:
    try:
        sections, citations = _summarize_outputs(state)

        if sections:
            details = "; ".join(sections)
        else:
            details = "no specialist mock outputs were available"

        intent_intro = {
            "nearest_pfz": "For the nearest fishing zone request",
            "safe_to_sail": "For the safe-to-sail request",
            "weather_tide": "For the weather or tide request",
            "geofence_check": "For the maritime boundary check",
        }.get(state.intent, "For this marine assistance request")

        state.final_answer = (
            f"{intent_intro}, this placeholder response uses mock data only: "
            f"{details}."
        )
        state.citations = citations

        if state.intent in {"safe_to_sail", "geofence_check"}:
            state.disclaimer = (
                "Safety note: this mock response is not a substitute for official "
                "IMD, INCOIS, coast guard, or local maritime advisories."
            )
        else:
            state.disclaimer = None

        state.trace.append(
            TraceEntry(
                agent="synthesizer",
                action="produce_final_answer",
                input_summary=f"intent={state.intent}; outputs={citations}",
                output_summary="Produced a placeholder final answer from mock data.",
                timestamp=datetime.utcnow().isoformat(),
            )
        )
    except Exception:
        state.final_answer = "Unable to generate a response at this time."
        state.citations = []
        state.disclaimer = None
        try:
            state.trace.append(
                TraceEntry(
                    agent="synthesizer",
                    action="produce_final_answer",
                    input_summary="synthesis failed",
                    output_summary="Returned a safe default response.",
                    timestamp=datetime.utcnow().isoformat(),
                )
            )
        except Exception:
            pass

    return state
