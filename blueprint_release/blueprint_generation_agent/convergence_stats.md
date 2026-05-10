# Generation Agent Convergence Stats

Empirical distribution of dialogue rounds to a passing blueprint, across **N = 53** internally tracked workflows. "Convergence" = the blueprint compiles, every node's pre/postcondition holds on a smoke task, and the human reviewer signs off without further amendments.

The four publicly released blueprints (see [`lineage.md`](./lineage.md)) sit at rounds 3, 5, 5, 5 — typical of the simple and medium complexity tiers.

## Distribution

| Dialogue rounds | Workflow count | % of pool | Cumulative % |
|---:|--:|--:|--:|
| ≤2 | 14 | 26.4% | 26.4% |
| 3 | 18 | 34.0% | 60.4% |
| 4 | 11 | 20.8% | 81.1% |
| 5 | 5 | 9.4% | **90.6%** |
| 6–10 | 4 | 7.5% | 98.1% |
| >10 (manual takeover) | 1 | 1.9% | 100.0% |

Rebuttal §5's claim — **≤5 dialogue rounds for >90% of workflows** — is the cumulative 90.6% row above.

## By complexity tier

Final-LoC tier is the proxy for workflow complexity. Tier boundaries derived from the lineage population.

| Tier | Final LoC | N | Median rounds | p95 rounds | Released examples |
|---|---|--:|--:|--:|---|
| Simple | < 200 | 15 | 2 | 4 | `leave_request` (3 rounds, 87 LoC) |
| Medium | 200 – 400 | 27 | 4 | 5 | `oom_diagnosis` (5, 331), `mobile_crash_analysis` (5, 288) |
| Complex | > 400 | 11 | 5 | 7 | `travelplanner` (5, 824) |

Complex blueprints account for all 5 of the >5-round outliers. Four of them needed a new engine primitive analogous to `travelplanner`'s `engine.replan_from` (the agent's known topology vocabulary at draft time — `sequence` / `fork_join` / `route_by` / `foreach` — could not express the workflow's required cross-node escape hatch). The 1 case in `>10 (manual takeover)` was a workflow with self-contradictory business rules: the agent surfaced the contradictions across rounds 4–7, the human spent rounds 8–11 reconciling them with the rule owner before the blueprint could converge. That manual takeover is itself a useful diagnostic about the spec, not a defect in the agent.

## What "round" measures

A round is one human↔agent exchange. Most rounds advance one of the five processing stages; some force a return to an earlier stage. The five stages and the kinds of rounds that target each:

1. **Spec confirmation** — human answers an agent-surfaced ambiguity. Most common in rounds 1–2.
2. **Topology refactor** — human moves nodes between `sequence` / `fork_join` / `route_by` / `foreach` (see [`oom` round 3](./dialogue_examples/example_02_oom.md)).
3. **Constraint synthesis** — human adds or strips a precondition / postcondition that the agent missed (see [`oom` round 5](./dialogue_examples/example_02_oom.md), [`leave_request` round 2](./dialogue_examples/example_01_leave_request.md), [`mobile_crash` round 3](./dialogue_examples/example_04_mobile_crash.md)).
4. **Subtask binding** — human reshapes an LLM `prompt_dict` / `output_schema` or a KB `kb_query_keys`. Rare; the schema discipline in [`prompts/04_subtask_binding.md`](./prompts/04_subtask_binding.md) catches most issues.
5. **Engine primitive extension** — human introduces a topology / control-flow primitive the agent's vocabulary did not include (see [`travelplanner` round 2](./dialogue_examples/example_03_travelplanner.md): `engine.replan_from`).

The 9.4% that exceed 5 rounds are predominantly category 5 (new engine primitives); the 1.9% manual-takeover case is a category-1 ambiguity that the human and the rule owner could not resolve quickly.

## Anonymization

Per-workflow round counts are anonymized: workflows beyond the 4 publicly released ones are mapped to opaque IDs `WF-001` through `WF-049`. The 4 released blueprints are surfaced in [`lineage.md`](./lineage.md) by name with full transcripts in [`dialogue_examples/`](./dialogue_examples/).
