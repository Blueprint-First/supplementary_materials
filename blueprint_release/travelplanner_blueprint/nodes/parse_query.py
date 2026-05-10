"""
Parse the natural-language travel request into a structured Goal.

query → Goal(description, cities, date_range, budget_allocated,
constraints, people_number, original_query).
"""

from sca.engine import node, postcondition

from ..blueprint import BP, Goal


@node(BP)
@postcondition(lambda ctx: ctx.get("goal") is not None and ctx["goal"].people_number >= 1)
def parse_query(ctx):
    """Parse raw query into a Goal dataclass."""
    raw = ctx["raw_query"]
    parsed = ctx["query_parser"].parse(raw)
    ctx["goal"] = Goal(
        description=parsed["description"],
        cities=parsed["cities"],
        date_range=parsed["date_range"],
        budget_allocated=float(parsed["budget"]),
        constraints=parsed.get("constraints", {}),
        original_query=raw,
        people_number=int(parsed.get("people_number", 1)),
    )
    return ctx
