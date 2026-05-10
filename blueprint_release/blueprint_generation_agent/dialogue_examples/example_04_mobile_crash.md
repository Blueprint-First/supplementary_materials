# Dialogue Example 4 — Mobile Crash Analysis Blueprint

> Anonymized human ↔ agent dialogue. Converged in 5 rounds. Final blueprint: 288 LoC. See [`../../se_blueprints/mobile_crash_blueprint.py`](../../se_blueprints/mobile_crash_blueprint.py).

## Round 1 — Elicitation

**Human:** Workflow for mobile (Android) Java crash analysis: take a batch of crash clusters, walk each one through summary → stack → source → root cause → suspect commit → remediation.

**Agent:** Four clarifications:

1. Input shape — raw JSON array, or wrapped `{data: [...]}` envelope, or both?
2. Crash types in scope — only `ANDROID_JAVA_CRASH`, or also `ANDROID_NATIVE_CRASH` / others?
3. Do we have a known-crashes KB to query before LLM analysis?
4. After analysis, do we want to auto-comment on the suspect commit, or only return a remediation hint?

## Round 2 — Spec confirm

**Human:**
1. Both shapes. Production payloads come either way; parser must accept both.
2. Java crashes for now. NATIVE crashes will register an empty interceptor list — engine should refuse routing rather than silently skip.
3. Yes — internal `known_crashes` KB indexed by exception class + top-frame signature.
4. Only return a remediation hint + suggested owner. Never auto-comment.

**Agent:** Noted. Will use `route_by(crash_type)` so unsupported / empty-chain types raise `"No interceptor found for crashType: ..."` locally as a structured routing error rather than silently skipping.

## Round 3 — Node graph

**Agent:** Proposed per-crash chain (after `parse_crash_list` + `route_by_crash_type`):

```
summary_analyse -> stack_analyse -> source_code_meta ->
    kb_query_known_crashes -> advanced_crash_analysis ->
    git_blame -> llm_remediation_hint
```

Top-level wraps this in `foreach(crash_list)`. LLM nodes: `advanced_crash_analysis` (root cause + suspect files) and `llm_remediation_hint` (text hint + suggested owner). KB sits between source resolution and LLM so the LLM is grounded.

**Human:** Order looks right. One concern: `git_blame` should be allowed to fail soft — if no candidate commits, set `error_msg` and stop the per-crash chain rather than abort the entire batch.

## Round 4 — Refine error semantics

**Agent:** Updated `git_blame` to set `ctx["error_msg"]` and skip downstream when no candidates. `llm_remediation_hint` now preconditions on `blame_commit is not None`. Compiled to 281 LoC. Smoke run on one ANDROID_JAVA_CRASH passes; one ANDROID_NATIVE_CRASH correctly stops at routing with `"No interceptor found"`.

## Round 5 — Compile and dry-run

**Agent:** Final compile to 288 LoC. Smoke batch (5 crashes mixed Java + Native) returns 4 ranked remediation hints + 1 routing-error record. Ready for review.

**Human:** Approved.
