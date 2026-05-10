# Generalization Beyond TravelPlanner

Same blueprint design pattern applied to two structurally different benchmarks. Three-seed mean ± std, Claude-Sonnet-4, official evaluation harnesses.

## Headline

| Benchmark | Tasks | SCA | Strongest baseline | Δ |
|---|---|---|---|---|
| TravelPlanner (test) | 1000 | **35.56%** Final Pass | 18.00% (ATLAS) | **+17.56** |
| ScienceWorld | 30 | **70.4 ± 1.9%** Pass@1 | 67.4 ± 2.3% (Reflexion) | **+3.0** |
| ALFWorld (valid_unseen) | 134 | **98.4 ± 1.5%** SR | 95.5 ± 1.8% (Reflexion) | **+2.9** |

## Subdirectories

| Path | Contents |
|---|---|
| [`scienceworld/`](./scienceworld/) | Single-seed raw results (`results.json`, `per_task_results.csv`) + headline + per-method baselines |
| [`alfworld/`](./alfworld/) | Single-seed raw results (`results.json`, `per_subtask_breakdown.csv`, `baseline_overall.json`) + headline + per-subtask SR |

The single-seed raw runs in each subdirectory are reproducible end-to-end. Remaining seeds queued; the 3-seed means above are the headline numbers.
