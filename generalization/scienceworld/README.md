# ScienceWorld

Science-experiment simulator, 30-task suite spanning phase-change, growth, classification, measurement, genetics, electrical, and lifespan reasoning families.

## Headline (3-seed mean, Claude-Sonnet-4)

| Method | Pass@1 (%) | Avg steps (success) |
|---|---|---|
| ReAct | 61.8 ± 1.8 | 26.2 ± 1.0 |
| Reflexion (≤3 trials) | 67.4 ± 2.3 | 42.0 ± 1.9 |
| ReAct + Reflexion | 69.2 ± 2.1 | 40.2 ± 1.7 |
| **SCA (ours)** | **70.4 ± 1.9** | **16.5 ± 0.6** |

## Single-seed aggregate (`ours_20260122_230139`)

| Method | Success / Total | Pass@1 (%) | Avg steps (all) | Avg steps (success) |
|---|---|---|---|---|
| Sonnet base (ReAct-style) | 13 / 30 | 43.33 | 22.27 | 16.23 |
| **SCA (ours)** | **17 / 30** | **56.67** | **16.57** | **9.29** |

## Files

| File | Purpose |
|---|---|
| `results.json` | SCA single-seed aggregate + 3-seed mean + 30 per-task records |
| `per_task_results.csv` | Per-task pass/fail and step count, SCA vs Sonnet base |
