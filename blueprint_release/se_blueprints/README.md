# Example Blueprints

Three reference blueprints cited in the rebuttal as evidence of authoring cost across a complexity spectrum:

| File | Role | KB | LLM | LoC |
|---|---|:-:|:-:|--:|
| [`leave_request_blueprint.py`](./leave_request_blueprint.py) | Lightweight rule-driven workflow (HR approval) | — | — | 87 |
| [`oom_blueprint.py`](./oom_blueprint.py) | Java OOM diagnosis (server-side, on-call workflow) | ✅ | ✅ | 331 |
| [`mobile_crash_blueprint.py`](./mobile_crash_blueprint.py) | Mobile (Android) crash analysis with per-CrashType routing | ✅ | ✅ | 288 |

All three blueprints are written against the same `sca.engine` API surface (`Blueprint`, `node`, `precondition` / `postcondition`, `retry` / `timeout`, `sequence` / `branch` / `fork_join` / `route_by` / `foreach`, `PostconditionFailure`, `engine.replan_from`) and the same `sca.tools` surface (`kb`, `llm`), so the engine semantics stay uniform regardless of workflow complexity.

## `@retry` semantics

Two distinct retry modes share the same decorator:

- **Plain transient-error retry** — `@retry(max_attempts=N, backoff_seconds=X)`. Used on IO nodes (HTTP / database / dump-store calls) where the failure is a transient infra hiccup. Example: `kb_query_*`, `git_blame`, `fetch_target_jvm`.
- **Postcondition-failure retry** — `@retry(max_attempts=N, on=PostconditionFailure, ...)`. Used on LLM nodes whose output may not satisfy the postcondition on the first draft. The engine re-invokes the same node with the same context; only `PostconditionFailure` triggers the retry, real exceptions still propagate. Example: `llm_root_cause`, `remediation_hint`, `advanced_crash_analysis`, `llm_remediation_hint`, and the four sub-planners in [`../travelplanner_blueprint/`](../travelplanner_blueprint/).

For cross-node failures (a downstream rule reveals an upstream defect), use `engine.replan_from(node, with_feedback=...)` from a verifier node — see `constraint_verify` in the TravelPlanner blueprint for a worked example.

Internal HR / dump-store / repo-index / git / notify adapters are stubbed via `ctx["xxx_api"]` injection — the production adapters will land in the public release once the framework decoupling roadmap completes (see [`../framework_roadmap.md`](../framework_roadmap.md)).
