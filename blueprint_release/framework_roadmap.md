# Framework Decoupling & Open-Source Roadmap

## Internal couplings to remove

| Coupling | What it does today | Decoupling plan |
|---|---|---|
| Service registry | Resolves blueprint nodes that call internal services | Replace with pluggable resolver interface; default to local registry |
| Authentication | Internal token-bound auth on every node side-effect | Replace with pluggable auth provider; default to no-op |
| Deployment orchestration | Runs blueprints on the internal scheduler | Replace with local executor; provide Kubernetes adapter as optional |
| Observability hooks | Emits to internal metrics/log pipeline | Replace with OpenTelemetry adapter |
| Internal blueprint registry | Stores production blueprints for reuse | Replace with file-based registry; optional remote backend |

## Milestones

| Milestone | Target |
|---|---|
| Resolver / auth / executor decoupled | T+4 weeks (post-acceptance) |
| OpenTelemetry adapter | T+6 weeks |
| First public release tag (`v0.1`) | T+8 weeks |
| Camera-ready link to public repo | before camera-ready deadline |

## What v0.1 will contain

- SCA execution engine (deterministic node graph, pre/post enforcement, retry semantics).
- LLM-tool wrappers for OpenAI / Anthropic / Google APIs.
- TravelPlanner / ScienceWorld / ALFWorld blueprints.
- Blueprint generation agent.
- Example blueprints (leave-request, crash-analysis — fully anonymized).
- Documentation: tutorial, API reference, blueprint-authoring guide.
