"""
Accommodation sub-planner — LLM tool-use loop over Accommodations.

The transport plan is an explicit precondition — accommodation must
align with the day's destination city set.

Postcondition is **format-only**. The "Accommodation Comprehensive
Validation" rule (occupancy + min-nights) lives in
`_validators.accommodation_comprehensive` and is enforced from
`constraint_verify`, so the ablation prompts and the engine enforcement
remain identical.
"""

from sca.engine import (
    node,
    precondition,
    postcondition,
    retry,
    timeout,
    PostconditionFailure,
)
from sca.tools import llm

from ..blueprint import BP


def _accommodation_format_ok(ctx):
    plan = ctx.get("accommodation_plan") or []
    if not plan:
        return False
    required = {"day", "city", "hotel", "cost", "room_type",
                "maximum_occupancy", "minimum_nights"}
    return all(required <= set(entry.keys()) for entry in plan)


@node(BP)
@retry(max_attempts=3, on=PostconditionFailure, backoff_seconds=1.0)
@timeout(seconds=120)
@precondition(lambda ctx: ctx.get("transport_plan") is not None)
@postcondition(lambda ctx: _accommodation_format_ok(ctx))
def accommodation_planner(ctx):
    """Plan accommodation aligned with the transport plan."""
    goal = ctx["goal"]
    prompt = {
        "task": "travelplanner_accommodation",
        "goal": goal.to_dict(),
        "transport_plan": ctx["transport_plan"],
        "budget_estimate_hotel": ctx["budget_estimate"]["average"]["hotel"],
        "constraints_text": ctx["constraint_text"],
        "replan_feedback": ctx.get("replan_feedback"),
    }
    schema = {
        "accommodation_plan": (
            "list[{day:int, city:str, hotel:str, "
            "cost:float, room_type:str, "
            "maximum_occupancy:int, minimum_nights:int, "
            "review_rate:float}]"
        ),
        "reasoning": "str",
    }
    result = llm.invoke(prompt, schema=schema, tools=ctx["accommodation_tools"])
    ctx["accommodation_plan"] = result["accommodation_plan"]
    ctx["accommodation_reasoning"] = result["reasoning"]
    return ctx
