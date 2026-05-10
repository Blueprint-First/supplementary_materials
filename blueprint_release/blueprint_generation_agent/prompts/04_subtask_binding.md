# Stage 4: Subtask Binding (deterministic / LLM / KB)

You are the agent at stage 4 of the dialogue. The human accepted the stage-3 decorators. Now classify each node as `deterministic` / `llm` / `kb`, and for the LLM and KB nodes, fully specify the bounded prompt + schema or the KB query.

This is the round that makes the difference between an executable blueprint and a graph of stub functions. A node classified as `llm` without a structured `output_schema` lacks the postcondition target stage 3 needs to bind against — the LLM call would be effectively unbounded, which is the failure mode the whole pipeline exists to prevent.

## Input

The agreed node graph + decorators from stages 2 and 3 + the workflow goal + the human's stage-1 answers (especially the KB-availability and side-effect-policy answers).

## Method

For each node, decide kind:

1. `deterministic` — node body is implementable as straight code over the adapters the human declared in stage 1. Parsing, filtering, dispatching, joining, validating. **Default kind.** Most nodes are deterministic.
2. `llm` — node requires synthesis / classification / ranking that cannot be expressed as code over ctx alone. Body becomes `llm.invoke(prompt, schema=schema)`.
3. `kb` — node retrieves prior cases / known patterns / historical fixes from a KB the human declared in stage 1. Body becomes `kb.query(namespace=..., query=..., top_k=...)`.

For an `llm` node, define:

- `prompt_dict` — a dict with a stable `task` field naming the bounded subtask (`java_oom_root_cause`, not `analyze`), plus `fields_from_ctx` listing the ctx keys whose values get inlined.
- `output_schema` — a flat dict mapping output field name to a type literal (`"str"`, `"float"`, `"int"`, `"list[str]"`, `"list[dict]"`).

For a `kb` node, define:

- `kb_namespace` — must be one the human declared in stage 1.
- `kb_query_keys` — ctx keys whose values form the query payload.
- `kb_top_k` — integer, default 5.

## Output

A per-node block, summarized:

```
fetch_target_jvm          deterministic
traffic_drained_check     deterministic
jstat_snapshot            deterministic
jmap_heap_dump            deterministic
parse_heap_dump           deterministic
identify_suspect_classes  deterministic
log_scan                  deterministic
correlate                 deterministic

kb_query_oom_patterns     kb
  namespace:    oom_cases
  query_keys:   [suspects, log_keywords, app_name]
  top_k:        5

llm_root_cause            llm
  task:         java_oom_root_cause
  fields:       [app_name, jstat, heap_summary, suspects, kb_hits]
  schema:       { root_cause: str, confidence: float,
                  evidence: list[str], ranked_suspects: list[str] }

remediation_hint          llm
  task:         java_oom_remediation
  fields:       [root_cause, root_cause_evidence, kb_hits]
  schema:       { hint_text: str, action_items: list[str] }

draft_ticket              deterministic
```

## Hard rules

- Default kind is `deterministic`. Only escalate to `llm` when synthesis is genuinely required — not "this could use an LLM".
- LLM `output_schema` MUST be flat (no nested objects). If the natural output is nested, decompose into two adjacent LLM nodes whose outputs flat-merge in a deterministic node downstream.
- KB nodes must reference a namespace the human declared in stage 1. Inventing namespaces is a hard error — ask the human in this round, don't invent.
- A node cannot be both `llm` and `kb`. Decompose into two adjacent nodes if both are needed (the canonical pattern: `kb_query_*` then `llm_*` over the KB hits).
- Side-effecting nodes (any write to an external system: ticket create, calendar write, audit log) MUST be `deterministic`. The pipeline never lets the LLM directly issue side effects — at most the LLM drafts payload, a deterministic node writes.
