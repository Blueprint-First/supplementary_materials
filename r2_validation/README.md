# R2 Validation — Three Seeds + Full 1000-Task Coverage

Per-seed raw plans backing the rebuttal sentence: *the repository includes plans for three validation seeds plus the full 1,000-task test run for cross-seed verification.*

## Coverage

| Asset | Tasks | Status |
|---|---|---|
| Validation × 3 seeds, SCA | 180 (idx 1–180), identical idx across seeds | complete |
| Validation × 1 seed, ReAct baseline | 179 (idx 1–180, 1 missing record) | seed-1 only |
| Test × 1 seed, SCA | 1000 (idx 0–999) | complete |
| Test × 1 seed, SCA + ReAct hybrid | 1000 (idx 0–999) | complete |
| Test × seeds 2, 3 | — | queued (~ 2 days each on internal cluster) |

## Headline numbers (Table III)

| Split | Method | Final Pass (%) |
|---|---|---|
| Validation (180) | SCA | **35.56** |
| Validation (180) | SCA + ReAct | **40.00** |
| Test (1000) | SCA | **27.10** |
| Test (1000) | SCA + ReAct | **34.10** |
| Test (1000) | ATLAS (strongest baseline) | 18.00 |

## Files

| Path | Contents |
|---|---|
| [`validation_seed{1,2,3}/`](./) | SCA plans on the 180-task validation split, three seeds |
| [`validation_seed1/plans_react.jsonl`](./validation_seed1/plans_react.jsonl) | ReAct baseline plans on the same set, seed 1 |
| [`test_seed1/`](./test_seed1/) | SCA + SCA-ReAct hybrid plans on the 1000-task test split |
| [`per_seed_summary.json`](./per_seed_summary.json) | Plan counts, day-distribution, idx coverage per file |
| [`seed_plan.md`](./seed_plan.md) | Three-seed protocol and camera-ready cross-seed plan |

JSONL schema: `{idx, query, plan}` — `plan` is the SCA-produced itinerary list.

## Re-scoring

```bash
# Inside the TravelPlanner repository:
python evaluation/eval.py --set_type validation \
    --plan_path <repo>/r2_validation/validation_seed1/plans_sca.jsonl
```

Emits `{Delivery, Commonsense Micro/Macro, Hard Constraint Micro/Macro, Final Pass}` per the metric definitions in §IV of the paper.
