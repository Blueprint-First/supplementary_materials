# Supplementary Materials — Blueprint First, Model Second (SCA)

Companion repository for the ICSME submission *Blueprint First, Model Second: A Framework for Deterministic LLM Workflow* and its rebuttal.

> **Visual landing page:** open [`index.html`](./index.html) in a browser for a card-based overview with status, headline numbers, and per-section links. This README is the GitHub-rendered fallback and contains the same map.

## Reviewer Quick Map

| Rebuttal claim | Where in this repo | Status |
|---|---|---|
| Fair-comparison ablation (constraints injected into baselines) | [`ablation/`](./ablation/) | SCA **37.2%** vs ATLAS 24.5% / CodeAct 19.0% / ReAct 17.0% on 100-task |
| SE case study (Java OOM, mobile crash) | [`se_case_study/`](./se_case_study/) | Trace examples here; blueprints in [`blueprint_release/se_blueprints/`](./blueprint_release/se_blueprints/) |
| Novelty positioning vs CodeAct | [`positioning/sca_vs_codeact.html`](./positioning/sca_vs_codeact.html) | Single-page visual walkthrough |
| Generalization (ScienceWorld, ALFWorld) | [`generalization/`](./generalization/) | 3-seed mean reported (70.4 ± 1.9% / 98.4 ± 1.5%); single-seed raw data in repo |
| Blueprint authoring cost & framework release | [`blueprint_release/`](./blueprint_release/) | TravelPlanner blueprint + generation agent + 3 example blueprints (87/331/288 LoC) |
| R2 validation seeds + 1000-task cross-seed plan | [`r2_validation/`](./r2_validation/) | 3 validation seeds (180 tasks each) + test seed 1 (1000 tasks) plans available |
| Long-form rebuttal (read-along) | [`REBUTTAL_DETAILED.md`](./REBUTTAL_DETAILED.md) | Reference document |

## Repository Layout

```
supplementary_materials/
├── index.html              # visual landing page (open in a browser)
├── README.md               # this file (GitHub-rendered fallback)
├── REBUTTAL_DETAILED.md    # long-form rebuttal with full data tables
├── ablation/               # 100-task fair-comparison ablation
├── se_case_study/          # Java OOM + mobile crash diagnosis
├── generalization/         # ScienceWorld + ALFWorld experiments
├── blueprint_release/      # TravelPlanner blueprint + generation agent + samples
├── positioning/            # SCA vs CodeAct positioning evidence
└── r2_validation/          # validation seeds + cross-seed protocol
```

Paper-text revisions (abstract / scope) are deferred to camera-ready.

Each subdirectory has its own README with the run commands and data schema.

## Conventions

- **Backbone:** Claude-Sonnet-4, temperature `0.7` (matches main paper Table I). Some cross-method comparisons additionally use GPT-5.2 / Gemini-2.5-Pro per Table I.
- **Evaluation:** TravelPlanner / ScienceWorld / ALFWorld official harnesses, no scoring modification.
- **Anonymity:** internal identifiers replaced with `<ENTERPRISE>`, `<APP>`, etc. If a reviewer spots any leak, please flag in the rebuttal forum.
- **Reproducibility:** Python ≥ 3.10. Each baseline run on full 1000-task TravelPlanner takes ≈ 2 days; the 100-task subset is provided for reviewer-reproducible turnaround.
