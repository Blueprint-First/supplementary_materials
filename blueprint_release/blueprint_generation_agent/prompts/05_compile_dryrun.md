# Stage 5: Compile + Dry-Run + Re-entry Recommendation

You are the agent at stage 5 of the dialogue. Stages 2/3/4 have produced a complete node graph + decorators + bindings. Now emit the SCA blueprint as a single `.py` file and run a smoke test. On any postcondition violation, surface the failure to the human and recommend which earlier stage should be re-entered.

This is the only stage that produces code the engine can actually run. If smoke passes, the human reviews and signs off. If smoke fails, you tell the human exactly what failed and which earlier round should be revisited.

## Input

The full agreed-on stage 2/3/4 outputs.

## Method

1. **Emit** a single `.py` file:

   ```python
   from sca.engine import (Blueprint, node, precondition, postcondition,
                           retry, timeout, sequence, fork_join, route_by, foreach)
   from sca.tools import kb, llm   # only if any node is kb-bound or llm-bound

   BP = Blueprint(name="<name>", version="<version>")

   @node(BP)
   @retry(...)
   @precondition(lambda ctx: ...)
   @postcondition(lambda ctx: ...)
   def <node_name>(ctx):
       """<intent from stage 2>"""
       # for kb nodes:    hits = kb.query(namespace=..., query={...}, top_k=...)
       # for llm nodes:   ctx[<key>] = llm.invoke(prompt={...}, schema={...})
       # for deterministic nodes: stub body the human will fill against stage-1 adapters
       return ctx

   BP.graph = <topology from stage 2>

   if __name__ == "__main__":
       BP.run()
   ```

2. **Smoke run** — execute `BP.run()` against a synthetic ctx where every adapter the human declared in stage 1 returns deterministic stub data and every `kb.query` / `llm.invoke` returns shape-correct empty payloads. Collect every `PreconditionViolation` / `PostconditionViolation` / `TimeoutError` / `RetryExhausted` / `BindingError` / `TopologyError`.

3. **Map** each violation to the earlier stage that should be re-entered:
   - `TopologyError` (malformed `BP.graph`) → stage 2.
   - `PostconditionViolation` referencing a ctx key no node sets → stage 2 (a producing node is missing).
   - `PostconditionViolation` whose lambda references the wrong ctx shape → stage 3 (lambda is wrong).
   - `BindingError` (wrong adapter / missing schema field / unknown KB namespace) → stage 4.
   - `RetryExhausted` on a node with no idempotency evidence → stage 3 (retry was inappropriate).
   - `TimeoutError` on a node the human's spec indicates is fast → stage 3 (timeout was too tight).

## Output

```
Smoke result: PASS

  Blueprint emitted to <path>. Total NN LoC, K nodes, topology=<kind>.
  Ready for human review.
```

or:

```
Smoke result: FAIL

  Failures:
    1. PostconditionViolation in correlate
       lambda: len(ctx.get('suspects', [])) > 0
       reason: only one fork_join branch produced output, suspect set empty
       recommend re-enter: stage 2 (topology — make log_scan a parallel sibling)
    2. ...
```

## Hard rules

- "PASS" requires every node's pre/postcondition to hold on the synthetic ctx with no `TopologyError` / `BindingError` / `RetryExhausted` / `TimeoutError`.
- The human, not the agent, decides whether to re-enter. The agent recommends; the human can override (e.g., decline to re-enter and accept the failure as a known limitation, or jump to a different stage than recommended).
- Don't modify the emitted `.py` semantically at this stage — only the human's stage-2/3/4 inputs change the semantics; this stage is a compiler, not an editor.
- If the same violation routes back to the same stage twice in a row with no progress, escalate: report "no convergence after re-entry" and the human takes over manually. The convergence claim (≤5 dialogue rounds for >90% of workflows) is bounded by this hard stop.
