# Deployment Scale (Mobile Crash)

> All numbers below are rounded to one significant figure to preserve anonymity.

| Metric | Value |
|---|---|
| App user base | tens of millions of DAU |
| Raw crash reports ingested per day | ~300,000 |
| Distinct crash clusters surfaced per day (after dedup at the reporting backend) | ~3,000 |
| Crash clusters routed through the SCA blueprint per day | ~800 (above triage threshold) |
| Mean time to suspect-commit (pre-SCA, manual triage by on-call mobile engineer) | ~4 hours |
| Mean time to suspect-commit (with SCA, ingest → draft ticket) | ~8 minutes |
| False-positive ticket rate (pre-SCA, runbook-driven) | ~30% |
| False-positive ticket rate (with SCA) | ~8% |
| `ANDROID_JAVA_CRASH` chain coverage | 100% (5/5 interceptors registered) |
| `ANDROID_NATIVE_CRASH` chain coverage | 0% (intentional — engine surfaces this as a localized "No interceptor found" error rather than silently skipping; native chain is on the roadmap) |
| KB hit rate against `known_crashes` index | ~55% |
| Draft tickets routed to the correct owning team on first try | ~85% |

The false-positive rate drop (30% → 8%) is driven by two structural factors, not by the LLM being smarter:

1. The `source_code_meta` node fails fast when the top app frame cannot be resolved against the repo index — those crashes are flagged for manual triage instead of being LLM-guessed into the wrong owning team.
2. The `git_blame` postcondition refuses to emit a ticket draft when `blame_rank` returns no candidates — previously a free-form agent would fabricate a "likely cause" from the stack alone.

The structured `emit_ticket_draft` step is intentionally non-autonomous — the engine emits a draft, a human reviews and confirms. This is the deterministic-agent posture for safety-critical SE workflows: the LLM is bounded to suggestion, never side-effect. Median human review time before accept is ~90 s when the KB hit is high-confidence and ~3 min otherwise.

The ~4 h → 8 min MTTR delta comes from collapsing four manual steps (read crash summary → eyeball stack → grep repo → guess release/commit) into the engine-driven `summary_analyse → stack_analyse → source_code_meta → kb_query_known_crashes → advanced_crash_analysis → git_blame → llm_remediation_hint` chain, plus skipping the human "have I seen this before?" step via KB lookup.
