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


def _answer_general_ocean_query(raw_query: str, language: str = "en") -> str:
    """Call Groq directly to answer a general ocean/marine knowledge question."""
    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")

        from groq import Groq

        client = Groq(api_key=api_key, timeout=15.0)
        print(
            f"SYNTHESIZER CALLING GROQ: model=openai/gpt-oss-120b, language={language}"
        )
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
                        "Answer the user's question in plain conversational text only, "
                        "as if you are speaking naturally to a person. "
                        "Your response must be 2 to 5 sentences or a short paragraph. "
                        "Do NOT use any markdown formatting whatsoever: no tables, no pipe "
                        "characters (|), no bold or italic asterisks, no numbered or "
                        "bulleted lists, no headers or hash symbols. "
                        "Do NOT invent specific real-time data. "
                        "End your answer by naturally weaving in the following disclaimer "
                        "as plain text within the same paragraph (not as a separate "
                        "section or header): 'Disclaimer: This is general knowledge and "
                        "does not reflect live or official data from INCOIS, IMD, or any "
                        "other authoritative source.' "
                        f"Write your response in the language with ISO code '{language}'. "
                        "If it is 'en', respond in English."
                    ),
                },
                {"role": "user", "content": raw_query},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"SYNTHESIZER LLM CALL FAILED: {e}")
        return (
            "I can share general ocean information, but I couldn't generate a full "
            "answer right now. Please try again."
        )


def _translate_static_message(message: str, language: str) -> str:
    """
    Translate a static English message into the target language via a one-shot
    Groq call. Falls back to the original English message on any failure.
    """
    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")

        from groq import Groq

        client = Groq(api_key=api_key, timeout=10.0)
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=256,
            temperature=0,
            reasoning_effort="low",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate the following English text into the language with "
                        f"ISO 639-1 code '{language}'. Return ONLY the translated text, "
                        "no extra commentary."
                    ),
                },
                {"role": "user", "content": message},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return message


def run(state: TurnState) -> TurnState:
    # -----------------------------------------------------------------------
    # out_of_scope — static friendly redirect, no LLM call needed.
    # -----------------------------------------------------------------------
    if state.intent == "out_of_scope":
        static_message = (
            "I'm ORCA, your ocean and maritime safety assistant. "
            "I can only help with topics related to ocean safety, fishing zones, "
            "tides, sea conditions, and maritime boundaries. "
            "Your question seems to be outside that scope — please rephrase or "
            "ask me something about the sea!"
        )

        # If the query is in a non-English language, translate the static message.
        if state.language != "en":
            static_message = _translate_static_message(static_message, state.language)

        state.final_answer = static_message
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
        answer = _answer_general_ocean_query(state.raw_query, language=state.language)
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
    # Original four intents — LLM-based answer with template fallback.
    # -----------------------------------------------------------------------
    try:
        sections, citations = _summarize_outputs(state)

        # Disclaimer logic (same in both LLM and fallback paths).
        if state.intent in {"safe_to_sail", "geofence_check"}:
            disclaimer = (
                "Safety note: this mock response is not a substitute for official "
                "IMD, INCOIS, coast guard, or local maritime advisories."
            )
        else:
            disclaimer = None

        # --- LLM path ---
        used_llm = False
        try:
            api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")

            from groq import Groq

            context_text = (
                "\n".join(sections)
                if sections
                else "No specialist agent outputs were available."
            )

            client = Groq(api_key=api_key, timeout=15.0)
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                max_tokens=300,
                reasoning_effort="low",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a friendly, concise marine safety assistant talking directly to a fisherman. "
                            "Write a natural, conversational answer in plain language based on the provided agent data. "
                            "Do NOT use raw field names like 'wind_speed_kmh' or dump code-like data. "
                            "If any agent's source is 'MOCK', explicitly and naturally mention within the sentence "
                            "that this is placeholder or mock data, not live yet — never silently present mock data as real. "
                            "Keep the answer to 2-4 sentences. Do not invent numbers beyond what is given. "
                            f"Write your response in the language with ISO code '{state.language}'. "
                            "If it is 'en', respond in English."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Agent data:\n{context_text}\n\nQuery: {state.raw_query}"
                        ),
                    },
                ],
            )
            state.final_answer = response.choices[0].message.content.strip()
            used_llm = True
        except Exception:  # noqa: BLE001
            # --- Template fallback ---
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

            lang_note = (
                f" [language: {state.language}]" if state.language != "en" else ""
            )
            state.final_answer = (
                f"{intent_intro}, this placeholder response uses mock data only: "
                f"{details}.{lang_note}"
            )

        state.citations = citations
        state.disclaimer = disclaimer

        output_summary = (
            "Produced conversational answer via Groq LLM."
            if used_llm
            else "Used fallback: Produced a placeholder final answer from mock data."
        )
        state.trace.append(
            TraceEntry(
                agent="synthesizer",
                action="produce_final_answer",
                input_summary=f"intent={state.intent}; outputs={citations}",
                output_summary=output_summary,
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
