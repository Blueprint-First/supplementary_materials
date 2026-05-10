"""
Attraction sub-planner — LLM tool-use loop over Attractions.

The Attractions data table has no price column, so this sub-planner does
NOT consume a budget envelope (consistent with `budget_estimation`,
which also omits attractions).

Postcondition is **format-only**. The "Activity-City Consistency
Validation" rule lives in `_validators.activity_city_consistency` and is
enforced from `constraint_verify`.
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


def _attraction_format_ok(ctx):
    plan = ctx.get("attraction_plan") or []
    if not plan:
        return False
    required_day = {"day", "city", "attractions"}
    required_attr = {"name", "city"}
    for day in plan:
        if not required_day <= set(day.keys()):
            return False
        for attr in day["attractions"]:
            if not required_attr <= set(attr.keys()):
                return False
    return True


@node(BP)
@retry(max_attempts=3, on=PostconditionFailure, backoff_seconds=1.0)
@timeout(seconds=120)
@precondition(lambda ctx: ctx.get("accommodation_plan") is not None)
@postcondition(lambda ctx: _attraction_format_ok(ctx))
def attraction_planner(ctx):
    """Plan attractions per day, locked to the day's accommodation city."""
    goal = ctx["goal"]
    prompt = {
        "task": "travelplanner_attraction",
        "goal": goal.to_dict(),
        "accommodation_plan": ctx["accommodation_plan"],
        "constraints_text": ctx["constraint_text"],
        "replan_feedback": ctx.get("replan_feedback"),
    }
    schema = {
        "attraction_plan": (
            "list[{day:int, city:str, "
            "attractions:list[{name:str, city:str, address:str, "
            "time_slot:str, est_duration_min:int}]}]"
        ),
        "reasoning": "str",
    }
    result = llm.invoke(prompt, schema=schema, tools=ctx["attraction_tools"])
    ctx["attraction_plan"] = result["attraction_plan"]
    ctx["attraction_reasoning"] = result["reasoning"]
    return ctx
