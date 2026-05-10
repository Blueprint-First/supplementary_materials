# Blueprint Generation Lineage

The four publicly released SCA blueprints went through the same five-stage dialogue (see [`README.md`](./README.md) and [`agent.py`](./agent.py)). This file is the per-blueprint summary.

## Per-blueprint

| Blueprint | Final LoC | Rounds | Major design decisions surfaced in dialogue | Transcript | Final blueprint |
|---|--:|--:|---|---|---|
| `leave_request` | 87 | 3 | `audit_log` node added between `write_calendar` and `notify` (round 2) | [example 1](./dialogue_examples/example_01_leave_request.md) | [`leave_request_blueprint.py`](../se_blueprints/leave_request_blueprint.py) |
| `oom_diagnosis` | 331 | 5 | `log_scan` moved into `fork_join` parallel with `parse_heap_dump → identify_suspect_classes` (round 3); `correlate` postcondition `len(suspects) > 0` added (round 5) | [example 2](./dialogue_examples/example_02_oom.md) | [`oom_blueprint.py`](../se_blueprints/oom_blueprint.py) |
| `travelplanner` | 824 | 5 | New `engine.replan_from(...)` primitive (round 2); `_validators.py` module split, `attraction_planner` precondition fix, `CATEGORY_TO_REPLAN_TARGET` map (round 3) | [example 3](./dialogue_examples/example_03_travelplanner.md) | [`travelplanner_blueprint/`](../travelplanner_blueprint/) (1 main + 11 nodes) |
| `mobile_crash_analysis` | 288 | 5 | `git_blame` soft-fail semantics (set `error_msg` instead of raise); `llm_remediation_hint` precondition on `blame_commit` (round 3) | [example 4](./dialogue_examples/example_04_mobile_crash.md) | [`mobile_crash_blueprint.py`](../se_blueprints/mobile_crash_blueprint.py) |

## What the agent does vs what the human does

| Agent | Human |
|---|---|
| Asks the irreducible clarifications a human would otherwise discover only at the smoke-run stage (stage 1) | Answers; rejects the irrelevant clarifications |
| Proposes a node decomposition + topology choice, with rationale (stage 2) | Accepts or rewrites the topology; flags missed parallelism (`oom` round 3 is the canonical case) |
| Drafts `@pre` / `@post` / `@retry` / `@timeout` lambdas grounded in stage-1 hard constraints (stage 3) | Catches scope errors (`oom` round 5: `correlate` postcondition added) |
| Classifies each node deterministic / LLM / KB; specifies prompt + schema (stage 4) | Approves; occasionally pushes back when the agent reaches for an LLM call where deterministic code suffices |
| Emits the `.py`, runs smoke, points at the earlier stage to revisit on failure (stage 5) | Decides whether to re-enter or accept as-is |

The `travelplanner` row is the largest authoring effort (+1 engine primitive, monolith → 12-file split). It is the case where the agent's existing topology vocabulary did not contain `replan_from` semantics, so a new engine primitive had to be introduced during round 2 — rounds 3-5 then refined the resulting graph.

## Cross-references in the rebuttal

| Rebuttal location | Backed by |
|---|---|
| §5 Released example sizes (`leave_request` / `oom_diagnosis` / `mobile_crash_analysis`) | The "Final LoC" column above (87 / 331 / 288). |
| §5 ">90% converge in ≤5 rounds" | [`convergence_stats.md`](./convergence_stats.md). |
| §5 quality sensitivity (debuggability) | The "Failure-mode demonstration" sections in `../se_case_study/<scene>/trace_example.md`. |
| §6 Release Plan — "Blueprint generation agent ✅ released" | [`agent.py`](./agent.py), [`prompts/`](./prompts/), [`dialogue_examples/`](./dialogue_examples/), [`convergence_stats.md`](./convergence_stats.md), this file. |
