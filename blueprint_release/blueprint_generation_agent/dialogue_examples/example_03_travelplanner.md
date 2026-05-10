# Dialogue Example 3 — TravelPlanner Blueprint

> Anonymized human ↔ agent dialogue for the TravelPlanner blueprint used in the headline experiment. Converged in 5 rounds. Final blueprint: 824 LoC across 1 main file + 11 node files (10 nodes + `_validators.py`). See [`../../travelplanner_blueprint/`](../../travelplanner_blueprint/).

## Round 1 — Elicitation

**Human:** I need a TravelPlanner blueprint that produces day-by-day itineraries: transport, hotel, dining, attractions, all within a budget. This is the headline benchmark — the constraints have to be auditable.

**Agent:** Five clarifications before I sketch the graph:

1. Where do the commonsense constraints live — encoded in a static rule registry, or queried from a KB at runtime?
2. How many sub-planners — one monolithic LLM call, or one per domain (transport / accommodation / dining / attraction)?
3. Are sub-planner outputs hard-validated, or are violations only surfaced post-hoc?
4. On a violation, do you want the engine to retry the same sub-planner, or to back up further and replan upstream?
5. What's the data layer — direct CSV/DB tools, or a wrapped tool layer?

## Round 2 — Spec confirm

**Human:**
1. Static rule registry. The fair-comparison ablation (rebuttal §1.1) injects every encoded constraint verbatim into baseline prompts, so constraints must be statically loadable and identifiable. No KB.
2. One per domain — four sub-planners. Accommodation depends on transport; dining and attractions only depend on accommodation and can run in parallel.
3. Hard-validated, but centralized: sub-planner postconditions stay format-only (required fields present), and a dedicated `constraint_verify` node enforces every semantic rule from the loaded registry. This way the engine's enforcement set is byte-identical to the rule set we inject into the §1.1 ablation baselines.
4. Both. A bad LLM draft retries the same node (`@retry(on=PostconditionFailure)`); a downstream rule revealing an upstream defect needs to back up to the originating sub-planner with structured feedback.
5. Tool layer wrapping the platform's `tools/` registry: Cities, Flights, Accommodations, Restaurants, Attractions, GoogleDistanceMatrix.

**Agent:** Noted. The "back up to originating sub-planner" requirement implies a new engine primitive — `engine.replan_from(node, with_feedback=...)`. Will register that semantic and use it from `constraint_verify` so cross-node failures route deterministically rather than aborting the chain.

## Round 3 — Node graph

**Agent:** Proposed:

```
parse_query
  -> load_constraints                  # static rule registry
  -> enumerate_cities
  -> budget_estimation                 # days × multipliers × unit prices
  -> transport_planner *               [postcond: format-only]
  -> accommodation_planner *           [precond: transport_plan exists;
                                        postcond: format-only]
  -> fork_join(
       dining_planner *,               [postcond: format-only]
       attraction_planner *,           [postcond: format-only]
     join=itinerary_assemble)
  -> constraint_verify                 [enforces ALL semantic rules;
                                        on fail -> engine.replan_from()]
  -> finalize_submission
```

* = LLM tool-use loop; all four wired with `@retry(max_attempts=3, on=PostconditionFailure)`.

`load_constraints` is a deterministic loader of `commonsense_constraints.json`, NOT a `kb.query` — see Round 2 answer 1.

**Human:** Order looks right. Three concerns:

1. `attraction_planner.precondition` should depend on `accommodation_plan`, not `transport_plan` — attractions need to know the day's lodging city, not the inter-city route.
2. `constraint_verify` needs an explicit category-to-replan-target map so cross-cutting rules (information_accuracy) abort cleanly rather than looping.
3. The validators behind each rule should live in one module (`_validators.py`) keyed by `rule_id`, so the rule registry's `id` field and the enforcement function are the same handle. Otherwise rule drift between JSON and Python is inevitable.

## Round 4 — Refine replan semantics + validator registry

**Agent:** All three fixed:

1. `attraction_planner.precondition = ctx.get("accommodation_plan") is not None`. Same for `dining_planner`. The fork-join branches both depend on accommodation but not on each other, so they still run in parallel.
2. `CATEGORY_TO_REPLAN_TARGET` added in `constraint_verify`; categories without a replan owner (e.g. `information_accuracy`) raise `UnrecoverableConstraintFailure` instead of looping.
3. New `nodes/_validators.py` exports `RULES: Dict[rule_id, callable]` and `RULE_CATEGORY: Dict[rule_id, str]`; `constraint_verify` looks up each rule by `rule["id"]` so the JSON registry and the Python enforcement function share a single handle.

Smoke task (3-day trip, $1500 budget, 2 people) runs end-to-end. One mid-run replan fires when the dining draft repeats a restaurant — engine re-enters `dining_planner` with `failed_rule_id="restaurant_global_uniqueness"` as feedback, the redraft is unique, downstream nodes proceed unchanged.

## Round 5 — Compile and dry-run

**Agent:** Final compile to 1 main + 11 node files. Smoke battery on a representative slice of the 100-task ablation subset passes `constraint_verify` on first attempt for the majority of tasks; the remainder trigger 1–2 replans each (most commonly on dining uniqueness or accommodation occupancy) and resolve on the next draft. Ready for review.

**Human:** Approved.
