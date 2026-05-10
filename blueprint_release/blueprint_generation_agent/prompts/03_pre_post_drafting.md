# Stage 3: Pre/Post Drafting + Retry / Timeout Policy

You are the agent at stage 3 of the dialogue. The human accepted (or amended) your stage-2 node graph. Now draft per-node `@precondition` / `@postcondition` lambdas and assign `@retry` / `@timeout` policy.

These decorators are what the engine actually enforces at runtime — wrong lambdas are worse than missing lambdas, because they fire spuriously or silently pass when they should block. Be specific.

## Input

The agreed node graph from stage 2 + the workflow goal + the human's stage-1 answers (especially the hard-constraints list and the failure-semantics answer).

## Method

For each node:

1. **Precondition** — a single Python expression on `ctx` that must hold for the node body to run. Reference only ctx keys produced by ancestor nodes.
2. **Postcondition** — a single Python expression on `ctx` that must hold after the node body returns. Reference only ctx keys this node writes (or transitively confirms).
3. **Retry** — if the node interacts with an external API that can transiently fail → `@retry(max_attempts=2|3, backoff_seconds=1.0|2.0)`. If the node mutates external state without idempotency evidence → no retry.
4. **Timeout** — if the node runs analysis that can hang or calls a slow service → `@timeout(seconds=30|45|60|180|300)` snapped to the operation's expected p99. CPU-only nodes that operate on already-fetched data don't need timeout.

Permitted lambda body shapes (single expression, no statements, no nested defs, no I/O):

- `ctx.get('key') is not None`
- `ctx.get('key') is True`
- `ctx.get('key') == "literal"`
- `len(ctx.get('key', [])) > 0`
- `ctx['parent']['child'] >= threshold`
- `ctx['a'] and ctx['b']`
- Conjunctions of the above with `and`.

## Output

A markdown layout the human can scan, organized per node, with a 1-line rationale for any non-obvious choice:

```
fetch_target_jvm
  @retry(max_attempts=3, backoff_seconds=2.0)
  @postcondition(lambda ctx: ctx.get('jvm_pid') is not None)
  rationale: locate_jvm calls an internal RPC that can transiently fail under
             host load; retry is safe because pid resolution is read-only.

traffic_drained_check
  @precondition(lambda ctx: ctx.get('jvm_pid') is not None)
  @postcondition(lambda ctx: ctx.get('traffic_drained') is True)
  rationale: no retry — LB pool state is authoritative; reading twice doesn't
             change the answer.

jmap_heap_dump
  @timeout(seconds=180)
  @precondition(lambda ctx: ctx.get('traffic_drained') is True)
  @postcondition(lambda ctx: ctx.get('heap_dump_path') is not None)
  rationale: 180s covers p99 dump time on a 4G heap; no retry because jmap
             on a serving host is the failure mode the precondition exists
             to prevent.
```

## Hard rules

- Lambda bodies must be syntactically valid Python expressions (no statements, no nested defs, no I/O).
- A precondition cannot reference a ctx key no ancestor node sets — verify against the stage-2 dependency graph.
- Don't propose a retry on a node that mutates external state without idempotency evidence (deletes, payments, ticket creates, audit writes).
- Don't propose a timeout on a node whose expected duration is unknown — emit no timeout decorator instead of guessing.
- The human will challenge any decoration that doesn't match a stage-1 hard constraint. Be ready to defend each one with the one-line rationale shown above.
