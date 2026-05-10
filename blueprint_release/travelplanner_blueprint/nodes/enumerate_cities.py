"""
Resolve the candidate city set from the destination state(s).
"""

from sca.engine import node, precondition, postcondition

from ..blueprint import BP


@node(BP)
@precondition(lambda ctx: ctx.get("goal") is not None)
@postcondition(lambda ctx: ctx.get("candidate_cities") and len(ctx["candidate_cities"]) > 0)
def enumerate_cities(ctx):
    """Enumerate candidate cities for each destination state in the goal."""
    cities_api = ctx["cities_api"]
    candidates = {}
    for state in ctx["goal"].cities:
        result = cities_api.run(state)
        if isinstance(result, list):
            candidates[state] = result
        else:
            ctx["error_msg"] = f"invalid state: {state}"
            candidates[state] = []
    ctx["candidate_cities"] = candidates
    return ctx
