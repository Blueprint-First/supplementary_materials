# SE Case Study

Anonymized industrial-deployment evidence for rebuttal §2 (ICSME venue fit). Two production SCA deployments inside `<ENTERPRISE>`, each with deployment-scale notes and an end-to-end execution trace.

| Case | Subdirectory | Trace | Scale notes | Blueprint |
|---|---|---|---|---|
| Java OOM diagnosis | [`java_oom/`](./java_oom/) | [`trace_example.md`](./java_oom/trace_example.md) | [`deployment_scale.md`](./java_oom/deployment_scale.md) | [`../blueprint_release/se_blueprints/oom_blueprint.py`](../blueprint_release/se_blueprints/oom_blueprint.py) |
| Mobile crash diagnosis | [`mobile_crash/`](./mobile_crash/) | [`trace_example.md`](./mobile_crash/trace_example.md) | [`deployment_scale.md`](./mobile_crash/deployment_scale.md) | [`../blueprint_release/se_blueprints/mobile_crash_blueprint.py`](../blueprint_release/se_blueprints/mobile_crash_blueprint.py) |

## Anonymization

- Service / app names, hostnames, internal URLs, and authentication paths are replaced with `<ENTERPRISE-...>` / `<HOST-X>` / `<APP-...>` placeholders.
- Deployment-scale numbers are rounded to one significant figure (explicit notice at the top of each `deployment_scale.md`).
- Stack frames in mobile crash traces use a synthetic but structurally faithful package layout (`com.<app>.feed.*`).

## What §VI of the camera-ready will add

- Problem framing per case (operational context, why a deterministic engine matters)
- Blueprint walkthrough mapped to each interceptor / sub-planner node
- Deployment metrics (incidents handled / week, MTTRC with vs without SCA, constraint-violation rate)
- Comparison against the prior runbook-based on-call workflow

The blueprints themselves are released now in [`../blueprint_release/se_blueprints/`](../blueprint_release/se_blueprints/); the trace and scale notes here are the read-along the rebuttal points reviewers to.
