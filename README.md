# Quantum Lab Agent

[繁體中文](README.zh-TW.md) · **0.1.0 (unreleased)** · [Apache-2.0](LICENSE)

A local Python CLI and React workbench for **classical LLM orchestration** of
bounded scientific tools. This is not a quantum LLM. Models plan tool calls;
validated tool evidence supplies the numeric reports.

- **Quantum:** standalone Qiskit/Aer CPU simulation of restricted Bell/GHZ
  circuits, noise, target verification, resource analysis, and plots. No QPU needed.
- **QEC:** sample/train/compare through an independently running external
  Project B HTTP service; B is not included in this repository.
- **Offline fixture:** fixed fake planner, real local Aer, mock QEC reports;
  useful for UI/API checks, not live Agent performance evidence.

## Quick start — no model key required

Use Python **3.12**, uv, and Node.js **22.12+** (UI). From the repository root:

```sh
uv sync --locked
uv run python scripts/quantum_smoke.py --output .qla/quantum-smoke
uv run uvicorn quantum_lab_agent.workbench_fixture:create_fixture_app --factory --host 127.0.0.1 --port 8100 --workers 1 --timeout-graceful-shutdown 5
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5174**; API docs: **http://127.0.0.1:8100/docs**.
Dependency installation needs package access; fixture execution needs no model
or B. The fixture banner and fixed behavior are intentional.

For a live model, follow [getting started](docs/getting-started.md) and
[configuration](docs/configuration.md). Live requests may incur cost. Run one
API worker/instance per data root; closing the browser does not cancel a run.

## Evidence, not a benchmark

Preserved NVIDIA Web smoke cases used **7 completions** total: Bell **43.222 s**
(4 calls), QEC **43.904 s** (3 calls), submit-to-finish. These are scoped,
one-attempt observations, not controlled latency comparisons or reliability
estimates. Historical Gemma failures remain available. Counts do not prove
quantum fidelity; ideal verification, noisy density-matrix fidelity, and model
termination are separate claims. See [results](docs/results.md),
[limitations](docs/limitations.md), and the [public evidence index](docs/evidence/README.md).

## Documentation

[Product requirements (Traditional Chinese)](docs/prd.zh-TW.md): users, workflows,
requirements, acceptance evidence, and the boundaries of version 0.1.0.

| Start / operate | Understand / reproduce |
|---|---|
| [Getting started](docs/getting-started.md) | [Architecture](docs/architecture.md) |
| [Workflows](docs/workflows.md) | [Project structure](docs/project-structure.md) |
| [Configuration](docs/configuration.md) | [Reproducibility](docs/reproducibility.md) |
| [Tool reference](docs/tool-reference.md) | [Evaluation](docs/evaluation.md) |
| [API reference](docs/api-reference.md) | [Results](docs/results.md) |
| [Troubleshooting](docs/troubleshooting.md) | [Limitations](docs/limitations.md) |
| [Roadmap](docs/roadmap.md) | [Release readiness](docs/release-readiness.md) |

The [original exhaustive usage guide](docs/legacy-usage.md) is retained as
historical documentation with relative links repaired for its new location.
See [public-copy provenance](docs/public-release.md); current instructions are above.

## Development and licensing

```sh
uv run --locked pytest -q
uv run --locked ruff check .
uv build
uv run --locked python docs/evidence/a3-nvidia-web-20261009/verify.py
```

In `frontend`, run `npm test` and `npm run build`. Checks use offline fixtures
and local simulation, not paid models. Hosted CI is authored, not yet executed.
See [Contributing](CONTRIBUTING.md), [Security](SECURITY.md),
[Code of conduct](CODE_OF_CONDUCT.md), [Changelog](CHANGELOG.md), and
[citation metadata](CITATION.cff).

Copyright 2026 JiuYang. Licensed under [Apache License 2.0](LICENSE).
Third-party dependencies retain their own licenses. No hosted release, package
publication, or remote repository is claimed by this local preparation.
