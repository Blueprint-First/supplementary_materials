# TravelPlanner Blueprint

Full runnable blueprint backing the TravelPlanner result in Table I/III. Wires a master pipeline + 4 sub-planner architecture; node-graph and pre/post are author-encoded so the constraints injected into the §1.1 ablation baselines are identifiable, line-for-line, in this directory.

## Quick start

```bash
pip install -r requirements.txt   # TODO add a requirements file
python -m blueprint_release.travelplanner_blueprint.blueprint \
    --backbone claude-sonnet-4 --task <task_id>
```

## Structure

```
travelplanner_blueprint/
├── blueprint.py                       # top-level node graph + Goal dataclass
├── nodes/                             # one file per subtask node
│   ├── parse_query.py                 # query → Goal
│   ├── load_constraints.py            # static rule registry (NOT a KB lookup)
│   ├── enumerate_cities.py            # Cities.run(state)
│   ├── budget_estimation.py           # days × multipliers × unit prices (mirrors source)
│   ├── _validators.py                 # rule_id → callable backing each commonsense rule
│   ├── transport_planner.py           # ★LLM + tool-use over Flights, GoogleDistanceMatrix
│   ├── accommodation_planner.py       # ★LLM + tool-use over Accommodations
│   ├── dining_planner.py              # ★LLM + tool-use over Restaurants
│   ├── attraction_planner.py          # ★LLM + tool-use over Attractions
│   ├── itinerary_assemble.py          # element_extraction + combination
│   ├── constraint_verify.py           # rule walk + engine.replan_from on failure
│   └── finalize_submission.py         # format_check + write submission
└── README.md
```

## Why no KB node here

The OOM and mobile-crash example blueprints both contain a `kb.query(...)` node (similar historical cases ground the LLM root cause). TravelPlanner intentionally does **not** route constraints through a KB:

- Rebuttal §1.1's fair-comparison ablation injects every constraint encoded in this blueprint verbatim into the baseline system prompts. That requires constraints to be **author-encoded and statically loadable** — `load_constraints` reads `constraint_rules/commonsense_constraints.json` directly.
- Routing constraints through a KB would force the question "where do the KB entries come from?" and dilute the ablation's premise.

`load_constraints` is therefore a deterministic loader, not a KB call.

## Constraint contract

Sub-planner postconditions are intentionally **format-only** (they check that the produced plan has the required fields and shape). All semantic rule enforcement is centralized in `constraint_verify`, which walks the rules loaded by `load_constraints` and dispatches each one to the matching callable in `_validators.RULES`. This single-path enforcement design has two consequences:

1. The rule set enforced by the engine is byte-identical to the rule set rebuttal §1.1 injects into the baseline system prompts — no rule lives in two places, no rule is implicit in a sub-planner helper.
2. The escape hatches are clean: `@retry(max_attempts=3, on=PostconditionFailure)` retries a sub-planner with the same context when the LLM draft is shape-broken; `engine.replan_from(node=<sub_planner>, with_feedback=...)` re-enters the originating sub-planner with structured feedback when a downstream rule reveals an upstream defect; `UnrecoverableConstraintFailure` aborts the chain when no replan target owns the violated rule.

The cross-node escape hatch is the architectural enforcement that rebuttal §1.3 attributes the residual 13-point SCA-vs-baseline gap to. The full enforcement layer is what the [`../../ablation/`](../../ablation/) study isolates.

