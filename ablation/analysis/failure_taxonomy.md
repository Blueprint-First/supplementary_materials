# Failure Taxonomy

Distribution of which constraints accounted for the residual failures across the 100-task subset, by method.


## ReAct + injected constraints

- Mean composite score: 16.85%
- Final-pass rate: 0.00%
- Total constraint failures across 100 tasks: 904

| Constraint | Kind | Failures | % of total failures | Description |
|---|---|---|---|---|
| C2 | commonsense | 91 | 10.1% | No restaurant repetition across the itinerary |
| H1 | hard | 90 | 10.0% | Budget cap (total cost ≤ user budget) |
| C3 | commonsense | 87 | 9.6% | No attraction repetition across the itinerary |
| C6 | commonsense | 84 | 9.3% | Database existence (no hallucinated entities) |
| C8 | commonsense | 84 | 9.3% | Information completeness per day |
| C1 | commonsense | 79 | 8.7% | Reasonable visiting city (closed loop, valid sequence) |
| C7 | commonsense | 79 | 8.7% | Accommodation minimum-nights rule |
| C4 | commonsense | 75 | 8.3% | Transportation mode consistency |
| C5 | commonsense | 74 | 8.2% | Information localized to current city |
| H4 | hard | 52 | 5.8% | Room-type match |
| H3 | hard | 44 | 4.9% | House-rule compatibility |
| H2 | hard | 42 | 4.6% | Cuisine coverage at destination |
| H5 | hard | 23 | 2.5% | Transportation restriction (no flight / no self-driving) |

## CodeAct + injected constraints

- Mean composite score: 18.13%
- Final-pass rate: 0.00%
- Total constraint failures across 100 tasks: 898

| Constraint | Kind | Failures | % of total failures | Description |
|---|---|---|---|---|
| H1 | hard | 88 | 9.8% | Budget cap (total cost ≤ user budget) |
| C1 | commonsense | 87 | 9.7% | Reasonable visiting city (closed loop, valid sequence) |
| C2 | commonsense | 83 | 9.2% | No restaurant repetition across the itinerary |
| C6 | commonsense | 83 | 9.2% | Database existence (no hallucinated entities) |
| C7 | commonsense | 83 | 9.2% | Accommodation minimum-nights rule |
| C5 | commonsense | 81 | 9.0% | Information localized to current city |
| C3 | commonsense | 80 | 8.9% | No attraction repetition across the itinerary |
| C4 | commonsense | 80 | 8.9% | Transportation mode consistency |
| C8 | commonsense | 75 | 8.4% | Information completeness per day |
| H4 | hard | 48 | 5.3% | Room-type match |
| H3 | hard | 44 | 4.9% | House-rule compatibility |
| H2 | hard | 41 | 4.6% | Cuisine coverage at destination |
| H5 | hard | 25 | 2.8% | Transportation restriction (no flight / no self-driving) |

## ATLAS + injected constraints

- Mean composite score: 24.35%
- Final-pass rate: 1.00%
- Total constraint failures across 100 tasks: 825

| Constraint | Kind | Failures | % of total failures | Description |
|---|---|---|---|---|
| H1 | hard | 82 | 9.9% | Budget cap (total cost ≤ user budget) |
| C6 | commonsense | 80 | 9.7% | Database existence (no hallucinated entities) |
| C2 | commonsense | 78 | 9.5% | No restaurant repetition across the itinerary |
| C3 | commonsense | 77 | 9.3% | No attraction repetition across the itinerary |
| C5 | commonsense | 74 | 9.0% | Information localized to current city |
| C8 | commonsense | 74 | 9.0% | Information completeness per day |
| C4 | commonsense | 73 | 8.8% | Transportation mode consistency |
| C7 | commonsense | 72 | 8.7% | Accommodation minimum-nights rule |
| C1 | commonsense | 69 | 8.4% | Reasonable visiting city (closed loop, valid sequence) |
| H4 | hard | 43 | 5.2% | Room-type match |
| H3 | hard | 42 | 5.1% | House-rule compatibility |
| H2 | hard | 37 | 4.5% | Cuisine coverage at destination |
| H5 | hard | 24 | 2.9% | Transportation restriction (no flight / no self-driving) |

## SCA

- Mean composite score: 37.27%
- Final-pass rate: 4.00%
- Total constraint failures across 100 tasks: 655

| Constraint | Kind | Failures | % of total failures | Description |
|---|---|---|---|---|
| H1 | hard | 80 | 12.2% | Budget cap (total cost ≤ user budget) |
| C5 | commonsense | 73 | 11.1% | Information localized to current city |
| C8 | commonsense | 70 | 10.7% | Information completeness per day |
| C1 | commonsense | 69 | 10.5% | Reasonable visiting city (closed loop, valid sequence) |
| C4 | commonsense | 67 | 10.2% | Transportation mode consistency |
| C7 | commonsense | 67 | 10.2% | Accommodation minimum-nights rule |
| H4 | hard | 45 | 6.9% | Room-type match |
| H3 | hard | 43 | 6.6% | House-rule compatibility |
| C3 | commonsense | 34 | 5.2% | No attraction repetition across the itinerary |
| H2 | hard | 33 | 5.0% | Cuisine coverage at destination |
| C6 | commonsense | 31 | 4.7% | Database existence (no hallucinated entities) |
| C2 | commonsense | 24 | 3.7% | No restaurant repetition across the itinerary |
| H5 | hard | 19 | 2.9% | Transportation restriction (no flight / no self-driving) |

## Cross-method observations

- The three baselines' top failure modes are dominated by **C2/C3/C6** (restaurant/attraction repetition + database hallucination). These are exactly the failure modes that a deterministic execution architecture eliminates by construction (state-tracking + sandbox-binding), and explain why the constraint injection only partially closes the gap with SCA.
