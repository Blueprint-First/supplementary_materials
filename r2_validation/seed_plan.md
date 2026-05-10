# Three-Seed Protocol

## Validation seeds (in this repo)

| Seed | File | Records | Avg plan length (days) |
|---|---|---|---|
| 1 | [`validation_seed1/plans_sca.jsonl`](./validation_seed1/plans_sca.jsonl) | 180 | 5.00 |
| 2 | [`validation_seed2/plans_sca.jsonl`](./validation_seed2/plans_sca.jsonl) | 180 | 5.01 |
| 3 | [`validation_seed3/plans_sca.jsonl`](./validation_seed3/plans_sca.jsonl) | 180 | 5.01 |

All three cover the identical idx 1–180 — per-seed scores are directly comparable per task.

## Test seed (in this repo)

| File | Records |
|---|---|
| [`test_seed1/plans_sca.jsonl`](./test_seed1/plans_sca.jsonl) | 1000 |
| [`test_seed1/plans_sca_react.jsonl`](./test_seed1/plans_sca_react.jsonl) | 1000 |

Test seeds 2 and 3 queued (≈ 2 days each on internal cluster).

## Configuration (all seeds)

- **Backbone:** Claude-Sonnet-4
- **Temperature:** 0.7 (matches Table I)
- **Eval harness:** official TravelPlanner script, no scoring modification
- **Stochasticity source:** Anthropic SDK seed parameter where the API honors it; otherwise natural sampling under temperature 0.7

## Camera-ready cross-seed protocol

1. Score each seed's `plans_sca.jsonl` against the official harness; collect Final Pass per seed per task.
2. Repeat for {SCA, ReAct, Reflexion, ReAct + Reflexion, ATLAS} on the 1000-task test set.
3. Report mean ± std per (method, metric) cell of Table III.
4. Paired McNemar test on seed-1 predictions for SCA vs each baseline; report p-values.

## Resource estimate

| Configuration | Wall-clock | Total runs | Total |
|---|---|---|---|
| 1 method × 1 seed × 1000 tasks | ≈ 2 days | 5 methods × 3 seeds = 15 | ≈ 30 days serial / ≈ 5 days at 6× cluster parallelism |

Validation (180 tasks) is much cheaper — already complete for SCA across all three seeds.
