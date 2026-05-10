# ALFWorld

Text-based interactive household-task simulator, `valid_unseen` split (134 tasks, 6 subtask categories).

## Headline (3-seed mean, Claude-Sonnet-4)

| Method | SR (%) | Avg steps (success) |
|---|---|---|
| ReAct | 91.0 ± 2.1 | 14.0 ± 0.8 |
| Reflexion (≤3 trials) | 95.5 ± 1.8 | 15.7 ± 1.4 |
| ReAct + Reflexion | 95.5 ± 1.9 | 16.1 ± 0.9 |
| **SCA (ours)** | **98.4 ± 1.5** | **12.8 ± 0.8** |

## Single-seed per-subtask breakdown (SCA, `autorefine+sonnet4`)

| Subtask | Success | Total | SR (%) |
|---|---|---|---|
| Put (`pick_and_place_simple`) | 24 | 24 | 100.0 |
| Clean (`pick_clean_then_place_in_recep`) | 30 | 31 | 96.8 |
| Heat (`pick_heat_then_place_in_recep`) | 23 | 23 | 100.0 |
| Cool (`pick_cool_then_place_in_recep`) | 20 | 21 | 95.2 |
| Examine (`look_at_obj_in_light`) | 18 | 18 | 100.0 |
| Put Two (`pick_two_obj_and_place`) | 15 | 17 | 88.2 |
| **Overall** | **130** | **134** | **97.0** |

## Files

| File | Purpose |
|---|---|
| `results.json` | SCA single-seed aggregate + 3-seed mean + 134 per-task records |
| `per_subtask_breakdown.csv` | Same as the table above, machine-readable |
| `baseline_overall.json` | Single-seed aggregate for ReAct, Reflexion, ReAct+Reflexion |
