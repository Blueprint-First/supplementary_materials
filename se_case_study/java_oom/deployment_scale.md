# Deployment Scale (Java OOM)

> All numbers below are rounded to one significant figure to preserve anonymity.

| Metric | Value |
|---|---|
| Target fleet size | tens of thousands of JVM hosts |
| Incidents handled per week | ~40 OOM clusters |
| Mean time to root cause (pre-SCA, manual on-call runbook) | ~30 minutes |
| Mean time to root cause (with SCA, alert → draft ticket) | ~5 minutes |
| Constraint-violation incidents (heap dump on production-traffic node) before introducing the precondition guard | ~6 per quarter |
| Constraint-violation incidents after introducing the precondition guard | 0 |
| LLM call budget per incident | 2 (root-cause pass + remediation hint) |
| KB lookup hit rate against historical OOM cases | ~70% |
| Draft tickets accepted by on-call without modification | ~60% |
| Draft tickets accepted after minor edit | ~30% |

The constraint-guard improvement above is the kind of correctness gain that motivates "Blueprint First, Model Second" — a deterministic engine refuses to run `jmap` on a node still serving production traffic; a stochastic agent would occasionally do it and degrade the user-facing service. The pre-guard incidents were not catastrophic (jmap-induced STW pause briefly tripped p99 latency on the affected host), but they were exactly the kind of latent failure a free-form agent has no structural reason to avoid.

The ~25-minute MTTR delta comes from collapsing four sequential manual steps (locate JVM → drain → run jstat / jmap → grep logs) into the engine-driven `fetch_target_jvm → traffic_drained_check → jstat_snapshot → jmap_heap_dump → fork_join(parse_heap_dump ‖ log_scan) → correlate` chain, plus skipping the human "have I seen this before?" step via the `kb_query_oom_patterns` node.
