"""
Run hard-constraint verification against the assembled itinerary; on
failure either trigger a targeted replan via `engine.replan_from` or
raise an unrecoverable failure.

Walks every rule loaded by `load_constraints` from
`constraint_rules/commonsense_constraints.json`, dispatching each one
to the matching callable in `_validators.RULES`. The
`engine.replan_from(node, with_feedback=...)` call is the architectural
enforcement that rebuttal §1.3 attributes the residual 13-point gap to:
when a downstream rule reveals an upstream defect, control returns to
the originating sub-planner with structured feedback rather than the
entire chain re-running.

Sub-planner postconditions only check output shape; ALL semantic rule
enforcement lives in this node so the enforcement path is single, clear,
and testable.
"""

from sca.engine import (
    node,
    precondition,
    postcondition,
    engine,
    UnrecoverableConstraintFailure,
)

from ..blueprint import BP
from ._validators import RULES, RULE_CATEGORY


# Maps the constraint-category to the sub-planner that owns the fix.
# Categories without a clear owner (cross-cutting information_accuracy)
# raise UnrecoverableConstraintFailure.
CATEGORY_TO_REPLAN_TARGET = {
    "transportation": "transport_planner",
    "accommodation": "accommodation_planner",
    "restaurant": "dining_planner",
    "planning": "attraction_planner",
}


@node(BP)
@precondition(lambda ctx: ctx.get("itinerary") is not None
              and ctx.get("constraints") is not None)
@postcondition(lambda ctx: ctx.get("verification_passed") is True)
def constraint_verify(ctx):
    """Walk every loaded rule; replan or raise on the first hard failure."""
    itinerary = ctx["itinerary"]
    goal = ctx["goal"]

    for rule in ctx["constraints"]:
        rule_id = rule["id"]
        validator = RULES.get(rule_id)
        if validator is None:
            raise UnrecoverableConstraintFailure(
                f"no validator registered for rule_id={rule_id!r}"
            )

        if validator(itinerary, goal, ctx):
            continue

        category = RULE_CATEGORY.get(rule_id, rule.get("category"))
        target = CATEGORY_TO_REPLAN_TARGET.get(category)
        if target is None:
            raise UnrecoverableConstraintFailure(
                f"rule {rule_id!r} (category={category!r}) failed and has no "
                f"replan target — itinerary needs human review"
            )

        # engine.replan_from raises ReplanRequested; control never returns
        # here — the engine re-enters `target` with the feedback attached
        # and resumes the chain from that point.
        engine.replan_from(
            node=target,
            with_feedback={
                "failed_rule_id": rule_id,
                "failed_rule_title": rule["title"],
                "rule_text": rule["rule_text"],
                "validation_hint": rule.get("validation"),
                "offending_itinerary": itinerary,
            },
        )

    ctx["verification_passed"] = True
    return ctx
