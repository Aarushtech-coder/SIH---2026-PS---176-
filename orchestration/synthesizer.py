import os
from datetime import datetime, timezone
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


def _answer_general_ocean_query(raw_query: str) -> str:
    """Call Groq directly to answer a general ocean/marine knowledge question."""
    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")

        from groq import Groq

        client = Groq(api_key=api_key, timeout=15.0)
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=512,
            temperature=0.3,
            reasoning_effort="low",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ORCA, a helpful marine and ocean knowledge assistant. "
                        "Answer the user's question clearly and concisely using your "
                        "general knowledge. Do NOT invent specific real-time data. "
                        "Always end your answer with a clear disclaimer in a new "
                        "paragraph: 'Disclaimer: This is general knowledge and does "
                        "not reflect live or official data from INCOIS, IMD, or any "
                        "other authoritative source.'"
                    ),
                },
                {"role": "user", "content": raw_query},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return (
            "I can share general ocean information, but I couldn't generate a full "
            "answer right now. Please try again."
        )


def run(state: TurnState) -> TurnState:
    # -----------------------------------------------------------------------
    # out_of_scope — static friendly redirect, no LLM call needed.
    # -----------------------------------------------------------------------
    if state.intent == "out_of_scope":
        state.final_answer = (
            "I'm ORCA, your ocean and maritime safety assistant. "
            "I can only help with topics related to ocean safety, fishing zones, "
            "tides, sea conditions, and maritime boundaries. "
            "Your question seems to be outside that scope — please rephrase or "
            "ask me something about the sea!"
        )
        state.citations = []
        state.disclaimer = None
        state.trace.append(
            TraceEntry(
                agent="synthesizer",
                action="produce_final_answer",
                input_summary=f"intent={state.intent}",
                output_summary="Returned out-of-scope static message.",
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        )
        return state

    # -----------------------------------------------------------------------
    # general_ocean_info — direct Groq LLM answer, no specialist agents.
    # -----------------------------------------------------------------------
    if state.intent == "general_ocean_info":
        answer = _answer_general_ocean_query(state.raw_query)
        state.final_answer = answer
        state.citations = []
        state.disclaimer = None
        state.trace.append(
            TraceEntry(
                agent="synthesizer",
                action="produce_final_answer",
                input_summary=f"intent={state.intent}; query={state.raw_query}",
                output_summary="Produced general ocean knowledge answer via Groq LLM.",
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        )
        return state

    # -----------------------------------------------------------------------
    # Four data-driven intents — LLM-primary, template-string fallback.
    # -----------------------------------------------------------------------
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

        state.citations = citations

        if state.intent in {"safe_to_sail", "geofence_check"}:
            state.disclaimer = (
                "Safety note: this mock response is not a substitute for official "
                "IMD, INCOIS, coast guard, or local maritime advisories."
            )
        else:
            state.disclaimer = None

        # --- Primary path: LLM-generated conversational answer ---
        llm_used = False
        try:
            api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")

            from groq import Groq

            # Build a compact context block using only non-null agent outputs.
            context_lines = []
            for agent_name, output in state.agent_outputs.items():
                if output is None:
                    continue
                source = output.source or agent_name
                context_lines.append(
                    f"- {agent_name} (source: {source}): {output.data}"
                )
            context_block = (
                "\n".join(context_lines)
                if context_lines
                else "No agent data was available."
            )

            system_prompt = (
                "You are ORCA, a friendly and concise marine safety assistant "
                "talking directly to a fisherman. "
                "Using only the data provided below, write a natural conversational "
                "answer in plain language — avoid raw field names like "
                "'wind_speed_kmh' or 'vessel_risk_score'; instead say things like "
                "'winds of about X km/h' or 'the risk is moderately high'. "
                "IMPORTANT: if any agent's source is 'MOCK', you MUST clearly and "
                "naturally say within your answer that the data is placeholder/mock "
                "and not live yet — do NOT silently present mock data as real. "
                "Keep the answer to 2-4 sentences. "
                "Do not invent specific numbers beyond what is in the provided data."
            )
            user_prompt = (
                f"Intent: {state.intent}\n"
                f"Agent data:\n{context_block}\n\n"
                "Write a short, friendly answer for the fisherman."
            )

            client = Groq(api_key=api_key, timeout=15.0)
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                max_tokens=300,
                temperature=0.4,
                reasoning_effort="low",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            llm_answer = response.choices[0].message.content.strip()
            if llm_answer:
                state.final_answer = llm_answer
                llm_used = True

        except Exception:
            pass  # Fall through to template fallback.

        # --- Fallback path: original template-string logic ---
        if not llm_used:
            state.final_answer = (
                f"{intent_intro}, this placeholder response uses mock data only: {details}."
            )

        state.trace.append(
            TraceEntry(
                agent="synthesizer",
                action="produce_final_answer",
                input_summary=f"intent={state.intent}; outputs={citations}",
                output_summary=(
                    "Produced final answer via Groq LLM."
                    if llm_used
                    else "Used template fallback (LLM unavailable)."
                ),
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
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
                    timestamp=datetime.now(tz=timezone.utc).isoformat(),
                )
            )
        except Exception:
            pass

    return state
