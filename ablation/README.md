# Fair-Comparison Ablation

Isolate the architectural enforcement from the constraint knowledge encoded in the SCA blueprint by injecting that knowledge into the baselines as system prompts and re-evaluating on a stratified 100-task TravelPlanner subset.

## Headline (mean per-task constraint-satisfaction)

| Method | Score on 100-task subset |
|---|---|
| ReAct + injected constraints | 16.9% |
| CodeAct + injected constraints | 18.1% |
| ATLAS + injected constraints | 24.4% |
| **SCA (ours)** | **37.3%** |

A ~13-point gap remains between SCA and the strongest baseline after equalizing constraint knowledge — this isolates the contribution of deterministic execution. Score = `(commonsense_micro + hard_micro) / 2 ∈ [0, 1]` per the official TravelPlanner scorers; full definition in [`methodology.md`](./methodology.md).

## Files

| Path | Purpose |
|---|---|
| `100task_subset.json` | Stratified subset (matches the full 1000-task difficulty distribution within ±2 pp per stratum) |
| `injected_prompts/` | The 13 constraints (8 commonsense + 5 hard) rendered as natural-language rules, per baseline |
| `results_100task.csv` | Per-task scores for all four methods |
| `runs/` | Per-method raw artifacts: `experiment_summary.json`, `generated_plans/`, `per_task_eval.jsonl` |
| `analysis/` | `failure_taxonomy.md` and `per_constraint_pass_rate.csv` |
| `methodology.md` | Subset construction, constraint extraction, injection protocol, evaluation |

## Reproduce

The runs in this directory were produced by the internal experiment harness (Claude-Sonnet-4 backbone, temperature 0, 100 tasks per method). The harness orchestrates:

1. Loading the 100-task subset (`100task_subset.json`).
2. For each baseline B in {ReAct, CodeAct, ATLAS}: prefixing the system prompt with `injected_prompts/B_injected.txt` (the verbatim text rendered from `_shared_constraint_block.txt`), then running B on each task.
3. Running SCA from `../blueprint_release/travelplanner_blueprint/`.
4. Scoring every plan with the official TravelPlanner `commonsense_constraint.py` + `hard_constraint.py` scorers and writing per-task / per-method records under `runs/<method>/`.

The harness depends on internal infrastructure (auth, deployment orchestration, observability) and is gated on the same decoupling roadmap as the SCA execution engine — see [`../blueprint_release/framework_roadmap.md`](../blueprint_release/framework_roadmap.md). A public reproduction CLI will be added once that decoupling lands.

In the meantime, the per-task `composite_score` in `results_100task.csv` and the per-task evaluation JSONL in `runs/<method>/per_task_eval.jsonl` are the auditable artifacts.
