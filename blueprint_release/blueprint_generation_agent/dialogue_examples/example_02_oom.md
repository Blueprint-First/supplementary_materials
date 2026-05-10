# Dialogue Example 2 — Java OOM Diagnosis Blueprint

> Anonymized human ↔ agent dialogue. Converged in 5 rounds. Final blueprint: 331 LoC. See [`../../se_blueprints/oom_blueprint.py`](../../se_blueprints/oom_blueprint.py).

## Round 1 — Elicitation

**Human:** Workflow for Java OOM diagnosis on production hosts: heap-dump inspection, log scan, and remediation hint.

**Agent:** Four clarifications:

1. Are heap dumps captured live (jmap) or pulled from a dump store?
2. Log scope — process-local only, or correlated across the cluster?
3. Do we have a historical OOM case knowledge base to query before LLM analysis, or is this a cold-start workflow?
4. Remediation: emit text hint, or also auto-create a ticket?

## Round 2 — Spec confirm

**Human:**
1. Live capture via jmap — but only on hosts already drained from production traffic.
2. Process-local stdout + service-wide ERROR log scan.
3. Yes — internal `oom_cases` KB indexed by suspect class + log keywords. Use it to ground the LLM.
4. Text hint + draft ticket. Never auto-create.

**Agent:** Noted the safety constraint on jmap. Will add a `traffic_drained_check` precondition on the dump node — engine refuses to run jmap on a serving host. Will wire a `kb_query_oom_patterns` node before the LLM root-cause pass so the LLM has grounded historical cases as context.

## Round 3 — Node graph

**Agent:** Proposed:

```
fetch_target_jvm -> traffic_drained_check ->
    jstat_snapshot -> jmap_heap_dump -> parse_heap_dump ->
    identify_suspect_classes -> log_scan -> correlate ->
    kb_query_oom_patterns -> llm_root_cause ->
    remediation_hint -> draft_ticket
```

LLM nodes: `llm_root_cause` (structured root cause + confidence + ranked suspects) and `remediation_hint` (KB-grounded LLM text hint + action items).

**Human:** `log_scan` should run in parallel with `parse_heap_dump → identify_suspect_classes`, then `correlate` joins both. Otherwise good.

## Round 4 — Refine to fork-join

**Agent:** Updated to a fork-join:

```
... -> jmap_heap_dump -> fork_join(
    branches=[
        sequence(parse_heap_dump, identify_suspect_classes),
        log_scan,
    ],
    join=correlate,
) -> kb_query_oom_patterns -> llm_root_cause ->
    remediation_hint -> draft_ticket
```

Compiled to 326 LoC. Smoke run on a synthetic dump fails at `correlate` because the join contract was missing a postcondition.

## Round 5 — Compile and dry-run

**Agent:** Added `correlate` postcondition `len(suspects) > 0`. Final compile to 331 LoC. Smoke test passes (synthetic dump → 3 suspects → 1 LLM root cause → KB-grounded hint → draft ticket). Ready for review.

**Human:** Approved.
