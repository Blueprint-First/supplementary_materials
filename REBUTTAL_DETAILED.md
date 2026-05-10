# Detailed Rebuttal — Long Form

Read-along for reviewers who want the underlying data behind the 800-word rebuttal. Per-claim methodology and raw records live in the corresponding subdirectory; this document collects the headline numbers and forward-looking notes in one place.

For a card-based visual overview, open [`index.html`](./index.html) in a browser.

---

## 1. Fair-Comparison Ablation

**Concern (R3-Q1 / R1):** SCA's gain could come from the constraint knowledge encoded in the blueprint rather than from the deterministic execution. We isolate by injecting the same constraint knowledge into the baselines as system prompts and re-evaluating.

**Setup:** stratified 100-task subset of TravelPlanner (matches the full 1000-task difficulty distribution). 13 constraints — 8 commonsense + 5 hard — extracted from the SCA TravelPlanner blueprint and rendered as natural-language rules, prefixed verbatim to each baseline planner. Backbone Claude-Sonnet-4. Per-task scoring `(commonsense_micro_pass + hard_micro_pass) / 2 ∈ [0, 1]`. Full protocol in [`ablation/methodology.md`](./ablation/methodology.md); 4 raw run sets in [`ablation/runs/`](./ablation/runs/).

| Method | Mean per-task constraint-satisfaction |
|---|---|
| ReAct + injected constraints | 16.9% |
| CodeAct + injected constraints | 18.1% |
| ATLAS + injected constraints (strongest baseline) | 24.4% |
| **SCA (ours)** | **37.3%** |
| **Δ vs strongest baseline** | **+12.9 points** |

A ~13-point gap remains after equalizing constraint knowledge — this isolates the contribution of deterministic execution. Per-task records in [`ablation/results_100task.csv`](./ablation/results_100task.csv); per-method run artifacts (experiment_summary, per_task_eval, generated plans) in [`ablation/runs/`](./ablation/runs/); failure taxonomy in [`ablation/analysis/failure_taxonomy.md`](./ablation/analysis/failure_taxonomy.md).

**Camera-ready:** the complete 1000-task ablation (3 baselines × 3 backbones × 3 seeds, ≈ 9 days at 6× cluster parallelism) replaces the 100-task subset in §V. Plan in [`ablation/roadmap.md`](./ablation/roadmap.md).

---

## 2. SE Case Study (ICSME Venue Fit)

**Concern (R1):** TravelPlanner is not an SE benchmark. Why this paper at ICSME?

**Position:** public SE benchmarks (SWE-bench, RepoBench) measure code synthesis; SCA targets *constrained workflow execution* — long-running multi-step diagnostic and operational procedures with hard correctness constraints. TravelPlanner stresses exactly that regime.

**Industrial evidence:** two anonymized production deployments inside `<ENTERPRISE>`:

| Case | Scale | Trace example | Blueprint |
|---|---|---|---|
| Java OOM diagnosis | clusters of tens of thousands of machines | [`se_case_study/java_oom/trace_example.md`](./se_case_study/java_oom/trace_example.md) | [`blueprint_release/se_blueprints/oom_blueprint.py`](./blueprint_release/se_blueprints/oom_blueprint.py) |
| Mobile crash diagnosis | app with tens of millions of DAU | [`se_case_study/mobile_crash/trace_example.md`](./se_case_study/mobile_crash/trace_example.md) | [`blueprint_release/se_blueprints/mobile_crash_blueprint.py`](./blueprint_release/se_blueprints/mobile_crash_blueprint.py) |

Both blueprints are stripped of internal service names, URLs, and authentication paths.

**Camera-ready:** §VI adds problem framing, blueprint walkthrough, deployment metrics (incidents handled / week, MTTRC with vs without SCA, constraint-violation rate), and comparison with prior runbook-based on-call workflows.

---

## 3. Novelty Positioning vs CodeAct

**Concern (R3-Q3):** how does SCA differ from CodeAct (Wang et al., ICML 2024)?

**Position:** different layers, composable. SCA is the workflow-control layer (deterministic, expert-authored); CodeAct is the execution / tool-use layer (LLM-generated code). The hybrid stacks them.

| | Layer | Authority over the next step | Failure mode |
|---|---|---|---|
| SCA | Workflow control | Deterministic, expert-authored program | Engine fails at the offending node, surfaces the missing precondition |
| CodeAct | Execution / tool use | LLM-generated code | Stochastic agent emits wrong action; debugging requires trace inspection |

Visual walkthrough: [`positioning/sca_vs_codeact.html`](./positioning/sca_vs_codeact.html) — same task under CodeAct alone, SCA alone, and the SCA + CodeAct hybrid.

**Camera-ready:** §II adds a positioning paragraph with citation to Wang et al. and a one-sentence note on the hybrid composition.

---

## 4. Generalization Beyond TravelPlanner

**Concern (R1 / R3):** are the gains TravelPlanner-specific?

**Setup:** same blueprint design pattern applied to two structurally different benchmarks, official evaluation harnesses, Claude-Sonnet-4, temperature 0.7, three-seed mean ± std.

| Benchmark | Tasks | SCA | Strongest baseline | Δ |
|---|---|---|---|---|
| TravelPlanner (test) | 1000 | **35.56%** Final Pass | 18.00% (ATLAS) | **+17.56** |
| ScienceWorld | 30 | **70.4 ± 1.9%** Pass@1 | 67.4 ± 2.3% (Reflexion) | **+3.0** |
| ALFWorld (valid_unseen) | 134 | **98.4 ± 1.5%** SR | 95.5 ± 1.8% (Reflexion) | **+2.9** |

The three benchmarks vary along orthogonal axes — domain (planning / scientific reasoning / household action), action space (structured queries / discrete primitives / discrete primitives), and horizon (long / medium / short) — yet all share the constraint-governed-procedure regime. Single-seed raw per-task records (one of three seeds for ScienceWorld and ALFWorld) in [`generalization/scienceworld/results.json`](./generalization/scienceworld/results.json) and [`generalization/alfworld/results.json`](./generalization/alfworld/results.json); remaining seeds queued.

**Scope note.** SCA is not designed to outperform free-form agents on tasks with no a-priori workflow (open-ended creative generation). And the cross-benchmark gain alone does not isolate architecture from constraint knowledge — that isolation is established by §1 above, where SCA still beats the strongest baseline by 12.7 points after the constraints are injected as system prompts.

---

## 5. Blueprint Authoring Cost

**Concern (R3-Q4):** is the blueprint cheap enough to author?

**Released example sizes:**

| Blueprint | LoC | Source |
|---|---|---|
| Leave request (lightweight rule-driven workflow) | 87 | [`blueprint_release/se_blueprints/leave_request_blueprint.py`](./blueprint_release/se_blueprints/leave_request_blueprint.py) |
| Java OOM diagnosis | 331 | [`blueprint_release/se_blueprints/oom_blueprint.py`](./blueprint_release/se_blueprints/oom_blueprint.py) |
| Mobile crash diagnosis | 288 | [`blueprint_release/se_blueprints/mobile_crash_blueprint.py`](./blueprint_release/se_blueprints/mobile_crash_blueprint.py) |
| TravelPlanner (full, 11-node) | runnable | [`blueprint_release/travelplanner_blueprint/`](./blueprint_release/travelplanner_blueprint/) |

**Generation-agent convergence:** across the workflows we have tracked internally (>50 distinct blueprints), the human-in-the-loop dialogue converges in **≤5 rounds for >90%** of cases. Distribution and protocol in [`blueprint_release/blueprint_generation_agent/convergence_stats.md`](./blueprint_release/blueprint_generation_agent/convergence_stats.md). Per-workflow round counts are anonymized; aggregate stats finalized for the camera-ready.

**Quality sensitivity (debuggability):** when a blueprint omits a precondition, the engine fails at the parse node with a file-not-found error pointing exactly at the missing precondition. The failure surface is local and the fix is mechanical, in contrast to a stochastic agent's silent failure.

---

## 6. Release Plan

| Asset | Status |
|---|---|
| TravelPlanner blueprint (runnable, 11-node) | ✅ released — [`blueprint_release/travelplanner_blueprint/`](./blueprint_release/travelplanner_blueprint/) |
| Blueprint generation agent | ✅ released — [`blueprint_release/blueprint_generation_agent/`](./blueprint_release/blueprint_generation_agent/) |
| Example blueprints (3) | ✅ released — [`blueprint_release/se_blueprints/`](./blueprint_release/se_blueprints/) |
| Full SCA execution engine | 🚧 gated on decoupling from internal infrastructure — [`blueprint_release/framework_roadmap.md`](./blueprint_release/framework_roadmap.md) |

Released artifacts let reviewers (1) inspect deterministic-engine semantics, (2) reproduce the headline TravelPlanner blueprint, and (3) validate the authoring-cost claims.

---

## 7. Validation Seeds (R2)

**Concern (R2):** variance evidence; gap behavior with task complexity.

**In the repo now:**
- 3 validation seeds × 180 tasks (identical idx coverage 1–180), SCA plans
- Test seed 1 × 1000 tasks (idx 0–999), SCA and SCA+ReAct hybrid plans
- Per-seed plan-count summary in [`r2_validation/per_seed_summary.json`](./r2_validation/per_seed_summary.json)

**Camera-ready protocol** (3 seeds × {SCA, ReAct, Reflexion, ReAct+Reflexion, ATLAS} × full 1000-task test set; mean ± std per metric; paired McNemar test on seed-1 predictions for SCA vs each baseline) in [`r2_validation/seed_plan.md`](./r2_validation/seed_plan.md).

---

## 8. Presentation, Abstract, Scope

Manuscript-text revisions (abstract tightening for R3-Q2; scope clarification for R1's "Blueprint First, Model Second" framing) are deferred to the camera-ready manuscript. The 800-word rebuttal states the planned changes; we will incorporate them in one pass after acceptance to avoid double-edit churn.
