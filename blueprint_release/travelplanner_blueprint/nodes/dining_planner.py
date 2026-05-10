"""
Dining sub-planner — LLM tool-use loop over Restaurants.

Postcondition is **format-only**. The "Restaurant Global Uniqueness
Across Entire Trip" rule lives in
`_validators.restaurant_global_uniqueness` and is enforced from
`constraint_verify`.
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


def _dining_format_ok(ctx):
    plan = ctx.get("dining_plan") or []
    if not plan:
        return False
    for day in plan:
        if "day" not in day:
            return False
        for slot in ("breakfast", "lunch", "dinner"):
            meal = day.get(slot)
            if meal is None:
                continue  # missing-meal handled by required_field_completeness
            if not isinstance(meal, dict) or "name" not in meal or "cost" not in meal:
                return False
    return True


@node(BP)
@retry(max_attempts=3, on=PostconditionFailure, backoff_seconds=1.0)
@timeout(seconds=120)
@precondition(lambda ctx: ctx.get("accommodation_plan") is not None)
@postcondition(lambda ctx: _dining_format_ok(ctx))
def dining_planner(ctx):
    """Plan breakfast / lunch / dinner per day."""
    goal = ctx["goal"]
    prompt = {
        "task": "travelplanner_dining",
        "goal": goal.to_dict(),
        "accommodation_plan": ctx["accommodation_plan"],
        "budget_estimate_restaurant": ctx["budget_estimate"]["average"]["restaurant"],
        "constraints_text": ctx["constraint_text"],
        "replan_feedback": ctx.get("replan_feedback"),
    }
    schema = {
        "dining_plan": (
            "list[{day:int, city:str, "
            "breakfast:{name:str, cost:float, cuisine:str, rating:float}, "
            "lunch:{name:str, cost:float, cuisine:str, rating:float}, "
            "dinner:{name:str, cost:float, cuisine:str, rating:float}}]"
        ),
        "reasoning": "str",
    }
    result = llm.invoke(prompt, schema=schema, tools=ctx["dining_tools"])
    ctx["dining_plan"] = result["dining_plan"]
    ctx["dining_reasoning"] = result["reasoning"]
    return ctx
