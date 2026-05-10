# Stage 2: Node Decomposition + Topology

You are the agent at stage 2 of the dialogue. The human has answered your stage-1 clarifications. Now propose a SCA node graph and submit it for human review.

This is the round where the topology takes shape. Get it right and stages 3-5 follow mechanically; get it wrong and the human will redirect the whole graph in a stage-2 second pass (see `dialogue_examples/example_02_oom.md` round 3 for the canonical case — `log_scan` was emitted sequential, the human moved it into a `fork_join` parallel branch).

## Input

The workflow goal + the human's answers to your stage-1 questions.

## Method

1. Walk the workflow conceptually from input to output. Each phase that has one tool / one concern / one observable output becomes a candidate node.
2. Name each node `snake_case` with a verb-first intent (`fetch_target_jvm`, `parse_heap_dump`, `kb_query_oom_patterns`, `llm_root_cause`, `draft_ticket`).
3. Identify dependencies: node B depends on A iff B reads ctx keys that A writes.
4. Identify parallelism: nodes whose ctx writes don't conflict and that share no dependency edge can be `fork_join`-parallel. Don't force parallelism — only propose it when latency matters or the branches are clearly independent.
5. Choose the topology root:
   - `sequence` — pure linear pipeline. Default.
   - `fork_join(branches=[...], join=<node>)` — at least two independent branches converge at a join.
   - `route_by(key=<ctx_key>, cases={...})` — exactly one ctx key drives mutually exclusive sub-pipelines (the per-CrashType dispatch in `mobile_crash_blueprint.py`).
   - `foreach(list_key, item_key=<ctx_key>, body=<sub-topology>)` — repeat a sub-pipeline per element of a ctx list (per-crash chain in mobile_crash).

Topologies nest. A `sequence` can contain a `fork_join`; a `foreach.body` can be any of the four.

## Output

A node graph proposal. Use this layout (markdown + ASCII), so the human can read and react:

```
Proposed graph:

    fetch_target_jvm
    -> traffic_drained_check
    -> jstat_snapshot
    -> jmap_heap_dump
    -> parse_heap_dump
    -> identify_suspect_classes
    -> log_scan
    -> correlate
    -> kb_query_oom_patterns
    -> llm_root_cause
    -> remediation_hint
    -> draft_ticket

LLM nodes: llm_root_cause (root cause + confidence + ranked suspects),
           remediation_hint (KB-grounded text hint + action items)
KB nodes:  kb_query_oom_patterns (namespace=oom_cases)
```

Then surface 1–2 design decisions you want the human to react to (e.g., *"I made `log_scan` sequential after `parse_heap_dump`; if scan-vs-parse latency matters, say so and I'll move it into a fork_join branch"*).

## Hard rules

- Every node must correspond to one phase the human's spec implies. No nodes invented for "future flexibility".
- Don't decorate yet — `@precondition` / `@postcondition` / `@retry` / `@timeout` come at stage 3.
- Don't bind LLM/KB calls yet — the prompt body and schema come at stage 4.
- If you propose `fork_join`, the join node must read ctx keys from every branch — otherwise it's not a real join.
- If you propose `route_by`, the cases must be exhaustive over the values the spec implies. An unobserved value should route to an explicit empty `sequence()` so the engine surfaces it as a localized routing error rather than a silent fall-through (this is what the `ANDROID_NATIVE_CRASH` route does in `mobile_crash_blueprint.py`).
- Tool references for any node must be tools the human declared in stage 1 (plus `kb` / `llm` for KB / LLM-bounded nodes). Inventing tools is a hard error — ask the human in this round, don't invent.
