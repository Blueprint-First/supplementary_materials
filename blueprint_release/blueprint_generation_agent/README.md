# Blueprint Generation Agent

The agent that turns a natural-language workflow specification into an SCA blueprint through a structured dialogue. Convergence claim made in the rebuttal: **≤5 dialogue rounds for >90% of workflows**.

## Files

| File | Purpose |
|---|---|
| [`agent.py`](./agent.py) | Dialogue orchestrator (5 stages, REPL driver, transcript logger) |
| [`prompts/01_workflow_elicitation.md`](./prompts/01_workflow_elicitation.md) | Stage 1 — agent surfaces 2–5 clarifying questions about goal, hard constraints, and tool boundaries |
| [`prompts/02_node_decomposition.md`](./prompts/02_node_decomposition.md) | Stage 2 — agent proposes node graph + topology (`sequence` / `fork_join` / `route_by` / `foreach`) |
| [`prompts/03_pre_post_drafting.md`](./prompts/03_pre_post_drafting.md) | Stage 3 — agent drafts `@precondition` / `@postcondition` / `@retry` / `@timeout` per node |
| [`prompts/04_subtask_binding.md`](./prompts/04_subtask_binding.md) | Stage 4 — agent classifies each node as deterministic / LLM-bounded / KB-querying; specifies `prompt` + `schema` or `kb.query(...)` |
| [`prompts/05_compile_dryrun.md`](./prompts/05_compile_dryrun.md) | Stage 5 — agent emits `.py` + smoke-runs + recommends which earlier stage to revisit on failure |
| [`dialogue_examples/example_NN_*.md`](./dialogue_examples/) | End-to-end dialogue traces — 4 worked examples (`leave_request`, `oom_diagnosis`, `travelplanner`, `mobile_crash_analysis`) |
| [`lineage.md`](./lineage.md) | Per-blueprint summary: rounds, author time, final LoC, design decisions surfaced in dialogue |
| [`convergence_stats.md`](./convergence_stats.md) | Empirical convergence distribution across tracked workflows |

## Dialogue stages

Five processing stages (`prompts/01..05`). A single round of dialogue typically advances one stage; sometimes a human reaction in round N forces a return to stage M < N (the topology refactor in [`example_02_oom.md`](./dialogue_examples/example_02_oom.md) round 3 is the canonical case — agent had emitted `log_scan` sequential, human moved it into a `fork_join` parallel branch).

```
spec ──► ┌──────────────────────────────┐
         │ 1. Workflow elicitation      │   agent asks clarifying questions
         └──────────────────────────────┘
                ▼ human answers
         ┌──────────────────────────────┐
         │ 2. Node decomposition        │   agent proposes nodes + topology
         └──────────────────────────────┘
                ▼ human accepts / amends
         ┌──────────────────────────────┐
         │ 3. Pre/post drafting         │   agent drafts decorators
         └──────────────────────────────┘
                ▼ human reviews
         ┌──────────────────────────────┐
         │ 4. Subtask binding           │   agent binds LLM/KB calls
         └──────────────────────────────┘
                ▼ human reviews
         ┌──────────────────────────────┐
         │ 5. Compile + dry-run         │   agent emits .py + smoke
         └──────────────────────────────┘
                ▼
        smoke PASS ──► human approves ──► blueprint ships
        smoke FAIL ──► agent recommends re-entry to stage 2/3/4 ──► loop
```

## Convergence claim

Across the workflows we have tracked internally, the dialogue converges in **≤5 rounds for >90% of cases**. The four publicly released blueprints — `leave_request` (3 rounds), `oom_diagnosis` (5), `travelplanner` (5), `mobile_crash_analysis` (5) — sit inside that distribution. Per-blueprint summary in [`lineage.md`](./lineage.md); full distribution in [`convergence_stats.md`](./convergence_stats.md).

## Run

```bash
python agent.py --llm-stub                       # interactive REPL with stub LLM
python agent.py --transcript out.md --llm-stub   # also log the dialogue to a file
```

`--llm-stub` uses the bundled `StubLLMClient` (echoes inputs — useful only for end-to-end shake-out). For real generation, implement the `LLMClient` Protocol against your provider of choice and pass it to `agent.run(...)`.
