"""Role 3 productivity-decline correlation agent.

Consumes observations supplied by the application. It does not invent catch
history or claim causation from a correlation. Each observation is a mapping
with catch, chlorophyll_mg_per_m3, and optional sst_celsius values.
"""

from datetime import datetime, timezone
import math

from orchestration.state import AgentOutput, TraceEntry, TurnState


def _correlation(first: list[float], second: list[float]) -> float | None:
    if len(first) < 2 or len(first) != len(second):
        return None
    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second)
    numerator = sum((a - first_mean) * (b - second_mean) for a, b in zip(first, second))
    denominator = math.sqrt(
        sum((a - first_mean) ** 2 for a in first)
        * sum((b - second_mean) ** 2 for b in second)
    )
    return round(numerator / denominator, 3) if denominator else None


def run(state: TurnState) -> TurnState:
    """Productivity agent entry point. Never raises per CONTRACTS.md resilience rule."""
    try:
        observations = getattr(state, "catch_history", None) or []
        valid_observations = []
        for item in observations:
            try:
                valid_observations.append(
                    {
                        "catch_kg": float(item["catch_kg"]),
                        "chlorophyll_mg_per_m3": float(item["chlorophyll_mg_per_m3"]),
                        "sst_celsius": (
                            float(item["sst_celsius"])
                            if item.get("sst_celsius") is not None
                            else None
                        ),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue

        catches = [item["catch_kg"] for item in valid_observations]
        chlorophyll = [item["chlorophyll_mg_per_m3"] for item in valid_observations]
        sst_items = [item for item in valid_observations if item["sst_celsius"] is not None]

        data = {
            "observations_used": len(valid_observations),
            "catch_chlorophyll_correlation": _correlation(catches, chlorophyll),
            "catch_sst_correlation": (
                _correlation(
                    [item["catch_kg"] for item in sst_items],
                    [item["sst_celsius"] for item in sst_items],
                )
                if len(sst_items) == len(valid_observations)
                else None
            ),
            "interpretation": (
                "Correlation is descriptive only; it does not establish causation."
                if valid_observations
                else "No catch-history observations supplied."
            ),
        }
        source = "DERIVED-FROM-PROVIDED-CATCH-HISTORY"
        output_summary = f"used {len(valid_observations)} catch-history observations"
    except Exception as e:
        # Resilience rule (CONTRACTS.md): never raise, fall back to mock
        data = {
            "observations_used": 0,
            "catch_chlorophyll_correlation": None,
            "catch_sst_correlation": None,
            "interpretation": f"Correlation analysis failed: {e}",
        }
        source = "MOCK"
        output_summary = f"Fell back to MOCK data due to: {e}"

    now = datetime.now(tz=timezone.utc).isoformat()
    state.agent_outputs["productivity_agent"] = AgentOutput(
        data=data,
        source=source,
        timestamp=now,
    )
    state.trace.append(
        TraceEntry(
            agent="productivity_agent",
            action="correlated supplied catch history with ocean indicators",
            input_summary=state.resolved_query,
            output_summary=output_summary,
            timestamp=now,
        )
    )
    return state
