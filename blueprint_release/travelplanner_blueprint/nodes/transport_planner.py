"""
Transport sub-planner — LLM tool-use loop over Flights + GoogleDistanceMatrix.

Postcondition is **format-only** (every day has a transportation entry
with the required fields). All semantic rules — including the "transport
cost ≤ budget envelope" check — live in `constraint_verify` via the
shared `_validators` module, so enforcement is single-path and the rules
injected into the §1.1 ablation prompts match the rules enforced here
byte-for-byte.

`@retry(on=PostconditionFailure)` covers LLM drafts that miss required
fields; `engine.replan_from` (from constraint_verify) covers semantic
violations discovered downstream.
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


def _transport_format_ok(ctx):
    plan = ctx.get("transport_plan") or []
    if not plan:
        return False
    required = {"day", "from", "to", "mode", "cost"}
    return all(required <= set(seg.keys()) for seg in plan)


@node(BP)
@retry(max_attempts=3, on=PostconditionFailure, backoff_seconds=1.0)
@timeout(seconds=120)
@precondition(lambda ctx: ctx.get("budget_estimate") and ctx.get("candidate_cities"))
@postcondition(lambda ctx: _transport_format_ok(ctx))
def transport_planner(ctx):
    """Plan inter-city transport for every day in the date range."""
    goal = ctx["goal"]
    prompt = {
        "task": "travelplanner_transport",
        "goal": goal.to_dict(),
        "candidate_cities": ctx["candidate_cities"],
        "budget_estimate_flight": ctx["budget_estimate"]["average"]["flight"],
        "constraints_text": ctx["constraint_text"],
        "replan_feedback": ctx.get("replan_feedback"),
    }
    schema = {
        "transport_plan": "list[{day:int, from:str, to:str, mode:str, cost:float, details:str}]",
        "reasoning": "str",
    }
    result = llm.invoke(prompt, schema=schema, tools=ctx["transport_tools"])
    ctx["transport_plan"] = result["transport_plan"]
    ctx["transport_reasoning"] = result["reasoning"]
    return ctx
