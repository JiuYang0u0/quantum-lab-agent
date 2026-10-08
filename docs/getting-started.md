# Getting started

[English](../README.md) · [繁體中文](../README.zh-TW.md)

Use Python **3.12** for the validated baseline, uv, and Node.js **22.12+** for
the UI. The package declares Python >=3.12; later Python versions are not a
tested compatibility promise. Windows is locally verified; Ubuntu is included
in the authored CI matrix, not yet executed on GitHub.

From the repository root:

```sh
uv sync --locked
uv run python scripts/quantum_smoke.py --output .qla/quantum-smoke
```

The smoke script runs actual CPU Aer circuits without a model, B, or API key.
Use a new output directory for a new record. Dependencies must first be installed;
“offline” refers to execution, not downloading packages.

## Offline UI

```sh
uv run uvicorn quantum_lab_agent.workbench_fixture:create_fixture_app --factory --host 127.0.0.1 --port 8100 --workers 1 --timeout-graceful-shutdown 5
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5174 (API docs: http://127.0.0.1:8100/docs).
The fixture banner is intentional. The fixed fake model ignores your prompt;
Quantum uses real local Aer, QEC uses mock reports. This is UI/API acceptance,
not evidence of autonomous model performance. This factory does not load `.env`.

## Live model mode (opt-in)

Stop the fixture API first. Configure the provider using
[configuration](configuration.md), then start:

```sh
uv run uvicorn quantum_lab_agent.workbench:create_app --factory --host 127.0.0.1 --port 8100 --workers 1 --timeout-graceful-shutdown 5
```

Use one worker, one instance, no reload. Production defaults to `.qla/workbench`;
fixture defaults to `.qla/acceptance-fixture`. Never share their data roots.
Select Quantum for standalone local simulation plus model planning. Select QEC
only with an independently installed/running Project B HTTP service.

Closing the browser does not cancel a run. Ctrl+C stops your server, but does not
guarantee cancellation of CPU work or B jobs. See [workflows](workflows.md).
Docker commands and historical detailed usage are preserved in the
[original guide](legacy-usage.md); Docker is optional, not a release prerequisite.
