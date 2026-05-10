"""
Format-check the verified itinerary and emit the TravelPlanner submission
record.

Runs only after `constraint_verify` has set `verification_passed=True`,
so it contains no fallback logic — by construction the input is valid.
"""

from sca.engine import node, precondition, postcondition

from ..blueprint import BP


@node(BP)
@precondition(lambda ctx: ctx.get("verification_passed") is True)
@postcondition(lambda ctx: ctx.get("submission_id") is not None)
def finalize_submission(ctx):
    """Format-check and write the final submission record."""
    submission = {
        "idx": ctx["task_idx"],
        "query": ctx["goal"].original_query,
        "plan": ctx["itinerary"],
        "metadata": {
            "trip_tier": ctx.get("trip_tier"),
            "budget_estimate": ctx.get("budget_estimate"),
            "rules_applied": [r["title"] for r in ctx["constraints"]],
        },
    }
    ctx["submission_id"] = ctx["submission_writer"].write(submission)
    return ctx
