"""
TravelPlanner SCA blueprint — top-level node graph + Goal dataclass.

The 11-node graph wires a master pipeline + 4 sub-planners (transport,
accommodation, dining, attraction), with hard-enforced postconditions
wired to the v2.0 commonsense constraint rules at
`constraint_rules/commonsense_constraints.json`.

Node ordering (* = LLM, none are KB — see rebuttal §1.1 for why
travelplanner does NOT route constraints through a KB):

    parse_query
      -> load_constraints                # static rule registry
      -> enumerate_cities
      -> budget_estimation               # days × multipliers × unit prices
      -> transport_planner *             [postcond: format-only]
      -> accommodation_planner *         [precond: transport_plan exists;
                                          postcond: format-only]
      -> fork_join(
           dining_planner *,             [postcond: format-only]
           attraction_planner *,         [postcond: format-only]
         join=itinerary_assemble)
      -> constraint_verify               [enforces ALL semantic rules;
                                          on fail -> engine.replan_from()]
      -> finalize_submission

Sub-planner postconditions are intentionally format-only; ALL semantic
rule enforcement is centralized in `constraint_verify` against the rule
set loaded by `load_constraints`. This keeps a single, identifiable
enforcement path — the same rule set that rebuttal §1.1's ablation
injects into baseline prompts.

`@retry(on=PostconditionFailure)` on each sub-planner covers LLM drafts
that miss required fields. `constraint_verify`'s `engine.replan_from(...)`
is the cross-node escape hatch when a downstream rule reveals an upstream
defect (this is the architectural enforcement that rebuttal §1.3
attributes the residual 13-point gap to).
"""

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

from sca.engine import Blueprint, sequence, fork_join


@dataclass
class Goal:
    """Top-level workflow goal: query metadata + budget + structured constraints."""
    description: str
    cities: List[str]
    date_range: List[str]
    budget_allocated: float
    constraints: Dict[str, Any] = field(default_factory=dict)
    original_query: str = ""
    people_number: int = 1

    def to_dict(self):
        return asdict(self)


BP = Blueprint(name="travelplanner", version="0.1.0")


# Node imports must come AFTER `BP` is defined — each node module decorates
# its function with `@node(BP)` at import time.
from .nodes.parse_query import parse_query  # noqa: E402
from .nodes.load_constraints import load_constraints  # noqa: E402
from .nodes.enumerate_cities import enumerate_cities  # noqa: E402
from .nodes.budget_estimation import budget_estimation  # noqa: E402
from .nodes.transport_planner import transport_planner  # noqa: E402
from .nodes.accommodation_planner import accommodation_planner  # noqa: E402
from .nodes.dining_planner import dining_planner  # noqa: E402
from .nodes.attraction_planner import attraction_planner  # noqa: E402
from .nodes.itinerary_assemble import itinerary_assemble  # noqa: E402
from .nodes.constraint_verify import constraint_verify  # noqa: E402
from .nodes.finalize_submission import finalize_submission  # noqa: E402


BP.graph = sequence(
    parse_query,
    load_constraints,
    enumerate_cities,
    budget_estimation,
    transport_planner,
    accommodation_planner,
    fork_join(
        branches=[dining_planner, attraction_planner],
        join=itinerary_assemble,
    ),
    constraint_verify,
    finalize_submission,
)


if __name__ == "__main__":
    BP.run()
