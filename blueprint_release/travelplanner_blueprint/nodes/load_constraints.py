"""
Load commonsense + hard constraints statically from the blueprint's
constraint registry.

Constraints are author-encoded JSON (priority + category + failure_rate +
validation), NOT a KB lookup — this is the artifact the rebuttal §1.1
ablation injects verbatim into baseline system prompts.
"""

from sca.engine import node, postcondition

from ..blueprint import BP


@node(BP)
@postcondition(lambda ctx: ctx.get("constraints") is not None and len(ctx["constraints"]) > 0)
def load_constraints(ctx):
    """Load CRITICAL + HIGH priority commonsense constraints."""
    loader = ctx["constraint_loader"]
    rules = loader.get_rules(priority=["CRITICAL", "HIGH"])
    ctx["constraints"] = rules
    ctx["constraint_text"] = loader.get_formatted_rules(
        priority=["CRITICAL", "HIGH"],
        include_header=True,
        include_stats=True,
    )
    return ctx
