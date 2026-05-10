# Blueprint Code & Generation Agent Release

Released for the rebuttal:

| Asset | Directory | Status |
|---|---|---|
| TravelPlanner blueprint (full, runnable) | [`travelplanner_blueprint/`](./travelplanner_blueprint/) | Released |
| Blueprint generation agent | [`blueprint_generation_agent/`](./blueprint_generation_agent/) | Released |
| Example blueprints (leave-request, oom, mobile-crash) | [`se_blueprints/`](./se_blueprints/) | Released |
| Full SCA execution engine | — | Roadmapped — see [`framework_roadmap.md`](./framework_roadmap.md) |

## Why partial release

The SCA execution engine is in production within `<ENTERPRISE>` and is deeply coupled with internal infrastructure: service registries, authentication paths, deployment orchestration, and observability hooks. A clean public release is infeasible within the rebuttal window. We are decoupling these internal dependencies and the full engine will be open-sourced once that work completes.

The artifacts released now are sufficient for reviewers to:

1. Inspect the deterministic-engine semantics (precondition, postcondition, node graph) — visible in the TravelPlanner blueprint.
2. Reproduce the headline TravelPlanner results — `travelplanner_blueprint/` is a fully runnable blueprint.
3. Validate the blueprint-authoring cost claims (≤5 dialogue rounds, 87/331/288 LoC examples) — `blueprint_generation_agent/` and `se_blueprints/`.
