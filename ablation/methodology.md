# Ablation Methodology

## Subset construction

The 100-task subset is sampled from the TravelPlanner test split with stratification on:

- Trip duration (3-day / 5-day / 7-day buckets)
- City count (single-city / multi-city)
- Constraint count (low / medium / high)

Stratification weights match the full 1000-task distribution to within ±2 percentage points per bucket. See `100task_subset.json` for the task IDs.

## Constraint extraction

Constraints encoded in the SCA TravelPlanner blueprint cover the full TravelPlanner evaluation surface — eight commonsense checks and five hard constraints that the official `commonsense_constraint.py` and `hard_constraint.py` scorers enforce.

**Commonsense constraints (logical / data integrity):**

1. Reasonable visiting city — first day departs from `org`, trip is a closed loop, intermediate cities appear consecutively for ≥ 2 days, all cities valid against `citySet_with_states.txt`.
2. No restaurant repetition — each restaurant in the entire itinerary may be visited at most once.
3. No attraction repetition — each attraction may be visited at most once.
4. Transportation consistency — first-day transport non-empty; `Self-driving` ⊕ `Flight`, `Self-driving` ⊕ `Taxi` mutual exclusion.
5. Information localized to current city — restaurants / attractions / accommodation belong to the day's current city, accommodation belongs to the destination on travel days.
6. Database existence (anti-hallucination) — flight numbers, drive/taxi routes, restaurants, attractions, hotels must match real records in the TravelPlanner sandbox.
7. Accommodation minimum-nights rule — consecutive stays satisfy each hotel's `minimum nights` requirement.
8. Information completeness (`is_not_absent`) — required fields populated per day, with travel-day vs. stay-day exceptions.

**Hard constraints (user-stated, query-dependent):**

9. Budget cap — total cost ≤ user budget; cost = transport + meals + lodging with per-vehicle and per-room occupancy rules.
10. Cuisine coverage — all cuisines listed in the query are tasted at the destination.
11. Room rule — selected accommodation permits required rules (smoking / parties / children / visitors / pets).
12. Room type — selected accommodation matches the requested type (shared / private / entire).
13. Transportation restriction — `no flight` / `no self-driving` clauses respected.

(Numbering 1-13 corresponds to `CONSTRAINTS.md` in the upstream TravelPlanner blueprint repo; constraints with `None` user value in the hard set are treated as vacuously satisfied per the official scorer.)

Each constraint was rendered as a natural-language rule and inserted as a system-prompt prefix to each baseline. See `injected_prompts/`.

## Injection protocol

For each baseline B in {ReAct, CodeAct, ATLAS}:

1. Take baseline B's original system prompt P_B.
2. Construct P_B' = `<injected constraints>` + P_B.
3. Run B on the 100-task subset using P_B'.
4. Score with the standard TravelPlanner scoring script.

No other modification to the baseline is made. This is the most charitable injection design we could specify — anything beyond this would be reimplementing SCA inside the baseline.

## Evaluation protocol

Single seed (TravelPlanner is deterministic given a fixed model temperature). Backbone: Claude-Sonnet-4 with **temperature 0** for the ablation. (Note: the main paper Table I and the generalization / R2 runs use temperature 0.7 to match the published baselines. The ablation deliberately drops to 0 to remove sampling variance from the comparison — the residual SCA-vs-baseline gap then reflects architectural contribution, not lucky sampling. The ATLAS + injected number reported here is the mean of two independent temperature-0 runs whose per-task scores agreed to 3 decimal places, confirming determinism at this setting.)

The per-task value reported in `results_100task.csv` is the TravelPlanner per-task constraint-satisfaction rate

```
score_i = ( commonsense_micro_pass_i + hard_micro_pass_i ) / 2   ∈ [0, 1]
```

where `*_micro_pass` is the fraction of applicable constraints in each family that the plan satisfies (the official scorer in `commonsense_constraint.py` / `hard_constraint.py`). `score_i = 1.0` is equivalent to the binary `Final Pass` criterion used in Table I of the paper. Reporting the continuous score on the 100-task subset preserves resolution under the small-N regime; the camera-ready 1000-task version will additionally report binary `Final Pass`.

The headline numbers in §1.3 of `REBUTTAL_DETAILED.md` are arithmetic means of `score_i` over the 100 tasks.

## Threats to validity

- **Single seed.** TravelPlanner outcomes have low variance under temperature 0; we report single-seed for the 100-task subset and will report three-seed in the camera-ready 1000-task version.
- **Subset size.** 100 tasks is sufficient to detect a ~13-point gap with p < 0.01 by McNemar's test on paired predictions; full 1000-task version follows.
- **Injection completeness.** The injected prompt may not exhaust the implicit knowledge in the SCA blueprint (e.g., control flow). This is exactly the gap the experiment is designed to measure — the residual is the architectural contribution.
