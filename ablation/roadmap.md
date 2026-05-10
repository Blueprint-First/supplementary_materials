# Camera-Ready Plan: Full 1000-Task Ablation

## Scope

Replace the 100-task subset result in §V with the full 1000-task TravelPlanner ablation run end-to-end after acceptance.

## Configuration matrix

| Axis | Values | N |
|---|---|---|
| Method | ReAct + injected, CodeAct + injected, ATLAS + injected, SCA | 4 |
| Backbone | Claude-Sonnet-4, GPT-5.2, Gemini-2.5-Pro | 3 |
| Seed | 1, 2, 3 | 3 |
| **Total runs** | | **36** (4 × 3 × 3) |

Each run scores all 1000 tasks with the official `commonsense_constraint.py` + `hard_constraint.py` scorers; per-task records and per-method aggregates land under `runs/<method>_<backbone>_seed<n>/` mirroring the current 100-task layout.

## Resource estimate

| Configuration | Wall-clock per run | Total wall-clock |
|---|---|---|
| Single (method × backbone × seed) on 1000 tasks | ≈ 2 days | 36 × 2 = 72 days serial |
| At 6× cluster parallelism (internal scheduler) | | **≈ 12 days end-to-end** |
| Schedule margin (retries, dataset reloads, scorer failures) | | +2 days |

Total: ~2 weeks from kickoff to results aggregation.

## Schedule

- **Acceptance notification → +1 week:** kick off all 36 runs in parallel on the internal cluster.
- **+3 weeks:** full results aggregated; cross-seed mean ± std computed; paired McNemar tests run on seed-1 predictions for SCA vs each baseline.
- **Camera-ready deadline:** §V replaced; relevant tables in §V regenerated; this README's headline replaced with the 1000-task numbers.

## Statistical protocol

For each (backbone, method) pair we report:

- Mean per-task `score_i` ± std across the 3 seeds (matches the 100-task `score_i` definition)
- Mean Final Pass rate ± std across the 3 seeds (binary metric used in Table I of the paper)
- Per-task paired McNemar test, SCA vs strongest baseline, on seed-1 predictions

Significance threshold p < 0.01 after Bonferroni correction over (3 backbones × 3 baselines = 9 comparisons).

## Deliverables added to this directory on completion

| File | Purpose |
|---|---|
| `results_1000task.csv` | Per-task records across all 36 (method × backbone × seed) runs |
| `runs/<method>_<backbone>_seed<n>/` | Per-run experiment summary, per-task eval, generated plans (32+ subdirectories) |
| `analysis/seed_variance.md` | Three-seed variance analysis per backbone |
| `analysis/mcnemar_tests.md` | Paired significance tests, SCA vs each baseline, per backbone |
| `analysis/per_constraint_pass_rate_1000task.csv` | Per-constraint pass rate at scale |
| `analysis/failure_taxonomy_1000task.md` | Failure-mode distribution by method × backbone |

The current 100-task subset (`100task_subset.json` + this directory's `runs/` and `analysis/`) is retained as the rebuttal-window reproduction artifact; the 1000-task results sit alongside it after camera-ready, not replacing it.

## What does NOT change

- Constraint set: the same 13 constraints (8 commonsense + 5 hard) extracted from the SCA TravelPlanner blueprint, injected verbatim into each baseline (see `methodology.md`).
- Injection protocol: prefix only; no other modification to the baseline planner.
- Scoring: official TravelPlanner scorers; no custom metric.

The architectural-enforcement claim of §1 only strengthens at scale — the 100-task subset already shows a 12.7-point gap (against the strongest baseline) after constraint equalization, and the full-set version controls additional sources of variance via the 3-seed × 3-backbone matrix above.
