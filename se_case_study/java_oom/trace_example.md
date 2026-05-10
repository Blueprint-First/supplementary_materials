# Java OOM Diagnosis — Anonymized Execution Trace

## Incident

- Service: `<ENTERPRISE-service-A>` (session-state microservice, ~200 JVM replicas)
- Symptom: 3 replicas in cluster `cluster-7` emitted repeated `java.lang.OutOfMemoryError: Java heap space` over a 12-minute window.
- Reporter: on-call alert from heap-pressure rule (`old_used_pct > 95% for 5m`).
- JVM heap config: `-Xmx4g -Xms4g`, G1GC.

## Input

The blueprint is invoked with the following initial `ctx` (alert-driven dispatcher fills these from the alert payload + service registry; adapter handles are wired by the engine):

```python
ctx = {
    # alert-driven inputs
    "target_host": "<HOST-A>",                 # one of the 3 firing replicas
    "app_name": "<ENTERPRISE-service-A>",
    "alert_id": "alert-2025-...-7Q",
    "alert_ts": 1762478931,                    # unix seconds, 2025-11-...
    "suspect_threshold_bytes": 50 * 1024 * 1024,
    "log_window_s": 600,

    # injected adapter handles (resolved from internal service registry)
    "jvm_ops":      <JvmOpsAdapter>,           # locate_jvm / jstat_gc / jmap_dump
    "lb_api":       <LoadBalancerAdapter>,     # is_in_pool
    "dump_store":   <DumpStoreAdapter>,        # allocate_path / stat
    "heap_parser":  <HeapParserAdapter>,       # parse(top_n=...)
    "log_api":      <LogServiceAdapter>,       # grep
    "ticket_api":   <TicketSystemAdapter>,     # draft (never auto-create)
}
```

No `kb` / `llm` handles are passed in `ctx` — those are resolved through the `sca.tools` module surface (`from sca.tools import kb, llm`) so the blueprint stays portable across deployments.

## SCA execution

| Step | Node | Outcome | Duration |
|---|---|---|---|
| 1 | `fetch_target_jvm` | PID `18244` resolved on `<HOST-A>`; uptime 9h 12m | 0.4 s |
| 2 | `traffic_drained_check` | Host confirmed out of LB pool (drained at alert time +30s by autoremediation) | 0.2 s |
| 3 | `jstat_snapshot` | `ygc=412 ygct=18.6s fgc=37 fgct=92.4s old_used_pct=98 metaspace_used_pct=61` | 0.3 s |
| 4 | `jmap_heap_dump` | 4.1 GB dump written to `<DUMP-STORE>/cluster-7/<HOST-A>/2025-...hprof` | 84 s |
| 5a | `parse_heap_dump` ‖ | Dominator tree built, 20 dominators retained | 142 s |
| 5b | `log_scan` ‖ | 14 matching ERROR lines around dump time (12 `OutOfMemoryError`, 2 `GC overhead`) | 6 s |
| 6 | `correlate` (join) | 3 suspects above 50 MB threshold cross-referenced with logs | 0.5 s |
| 7 | `kb_query_oom_patterns` | 3 historical hits; top hit `oom-2024-Q4-117` (score 0.81): "unbounded LRU cache for session entries" | 1.2 s |
| 8 | `llm_root_cause` | Root cause: "unbounded `SessionEntry` cache — TTL config defaulted to 0, eviction never triggered"; confidence 0.86 | 7.4 s |
| 9 | `remediation_hint` | "Set `sessionCache.ttlSeconds=900` in `<CONFIG-A>`; cap `maxEntries=50000`; add eviction-rate gauge to dashboard `<DASH-A>`" | 5.1 s |
| 10 | `draft_ticket` | Draft `TICKET-<NNNN>` created in `<TICKET-SYSTEM>`; routed to owning team `service-a-platform` | 0.8 s |

**Total wall-clock:** 4 min 8 s from `fetch_target_jvm` invocation to draft ticket. Alert-to-engine-start dispatch added another ~40 s, so end-to-end alert→ticket was ~5 min — matching the deployment-scale median.

### Top dominators (from step 5a)

| Rank | Class | Retained | Instances |
|---|---|--:|--:|
| 1 | `com.<enterprise>.session.SessionEntry` | 1.8 GB | 1,940,221 |
| 2 | `byte[]` (held via `SessionEntry.payload`) | 1.1 GB | 1,940,221 |
| 3 | `java.util.LinkedHashMap$Entry` | 220 MB | 1,940,224 |
| 4 | `java.util.concurrent.ConcurrentHashMap$Node` | 64 MB | 940,002 |
| 5 | other (cumulative) | 410 MB | — |

The `SessionEntry → byte[] → LinkedHashMap$Entry` retention chain (steps 1-3) corresponds 1:1 to the historical KB hit `oom-2024-Q4-117`, which is what surfaced the unbounded-LRU-cache hypothesis to the LLM root-cause pass.

## Output

The blueprint produces a structured `ticket_draft` (final node) plus the upstream artifacts that justify it. Final `ctx` snapshot (relevant keys only):

```python
ctx["root_cause"] = (
    "Unbounded LRU cache for SessionEntry — the per-instance ttlSeconds "
    "config defaulted to 0 after a recent config-schema migration, so the "
    "eviction loop short-circuited and entries accumulated until heap "
    "exhaustion."
)
ctx["root_cause_confidence"] = 0.86
ctx["root_cause_evidence"] = [
    "SessionEntry retains 1.8 GB across 1.94M instances (top dominator)",
    "byte[] (1.1 GB) reachable only via SessionEntry.payload",
    "fgc=37 with fgct=92.4s — collector unable to reclaim old gen",
    "KB case oom-2024-Q4-117 score 0.81 — same retention chain, same root cause",
    "log line 2025-...T... 'evicted=0 inserted=12041' — eviction loop never fired",
]
ctx["ranked_suspects"] = [
    "com.<enterprise>.session.SessionEntry",
    "byte[]",
    "java.util.LinkedHashMap$Entry",
]
ctx["remediation_hint"] = (
    "Set sessionCache.ttlSeconds=900 in <CONFIG-A>; cap maxEntries=50000; "
    "add eviction-rate gauge to dashboard <DASH-A> and a 5m alert on "
    "evicted/inserted < 0.1."
)
ctx["remediation_actions"] = [
    "config: set <CONFIG-A>.sessionCache.ttlSeconds=900 (currently 0)",
    "config: set <CONFIG-A>.sessionCache.maxEntries=50000 (currently unbounded)",
    "metrics: register sessionCache.evicted / sessionCache.inserted gauges",
    "alert: add 5m alert on evicted/inserted ratio < 0.1 to <DASH-A>",
    "rollout: canary on cluster-7 first, full fleet after 24h soak",
]

ctx["ticket_draft"] = {
    "id": "TICKET-<NNNN>",
    "status": "DRAFT",                        # never auto-promoted
    "title": "[OOM] <ENTERPRISE-service-A> — Unbounded LRU cache for SessionEntry — the per-instance ttlSec",
    "host": "<HOST-A>",
    "jvm_pid": 18244,
    "heap_dump_path": "<DUMP-STORE>/cluster-7/<HOST-A>/2025-...hprof",
    "ranked_suspects": [
        "com.<enterprise>.session.SessionEntry",
        "byte[]",
        "java.util.LinkedHashMap$Entry",
    ],
    "evidence": [...],                        # same as ctx["root_cause_evidence"]
    "kb_references": ["oom-2024-Q4-117", "oom-2024-Q2-052", "oom-2025-Q1-009"],
    "remediation_hint": "Set sessionCache.ttlSeconds=900 in <CONFIG-A>; ...",
    "action_items": [...],                    # same as ctx["remediation_actions"]
    "routed_to": "service-a-platform",
    "requires_human_review": True,
}
```

On-call accepted this draft after a 75-second review (no edits to title or action items; one comment added pointing to the prior config-migration PR). The fix shipped 6 hours later behind a canary on `cluster-7` and rolled fleet-wide after a 24h soak.

## Failure-mode demonstration

In a parallel test run we deliberately removed the `correlate` postcondition `len(suspects) > 0`. We then fed in a synthetic dump where every dominator was below the 50 MB threshold (so `identify_suspect_classes` produced an empty list) and the log scan returned no matches.

- **With the postcondition:** the engine halted at the `correlate` node with `PostconditionViolation: len(suspects) > 0`. The traceback pointed directly at the join — surfacing that *neither* branch (heap parse, log scan) had produced a usable signal. On-call's next step was obvious: investigate why the dump was uninformative (turned out to be a heap that had already been GC'd between OOM and snapshot).
- **Without the postcondition:** execution proceeded into `kb_query_oom_patterns` with an empty suspect set, which returned 0 hits; `llm_root_cause` was then asked to root-cause an empty payload and confidently emitted `"likely thread-local leak"` with confidence 0.71, citing no concrete evidence. The draft ticket was filed. A free-form agent baseline in the same configuration produced the same kind of confident-but-ungrounded ticket.

This is the qualitative debuggability gain we describe in §T7 of the rebuttal: structural failures produce localized, named violations rather than confidently-wrong downstream output.
