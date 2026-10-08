# Project structure

| Path | Purpose |
|---|---|
| [src/quantum_lab_agent](../src/quantum_lab_agent) | Python package; see [architecture](architecture.md) for module mapping |
| [tests](../tests) | Offline Python regressions and real local Aer checks |
| [frontend/src](../frontend/src) | React workbench, evidence rendering, Vitest tests |
| [config/providers.toml](../config/providers.toml) | Documented provider defaults |
| [scripts](../scripts) | Smoke, isolated B integration, opt-in live evaluations |
| [docs/evidence](evidence/README.md) | Preserved results, failed runs, traces, hashes, screenshots |
| [docs/notebooks](notebooks) | Local quantum notebook |
| [pyproject.toml](../pyproject.toml), [uv.lock](../uv.lock) | Python metadata and resolved dependencies |
| [frontend/package-lock.json](../frontend/package-lock.json) | Frontend dependency lock |
| [.github](../.github) | Authored CI and collaboration templates |
| [compose.yaml](../compose.yaml) | Optional A-only containers; B remains external |

Local `.qla/` stores trace databases, runs, and generated artifacts; `.env` stores
private settings. Both are ignored and are not release inputs. The Python wheel
contains the Python package/license, not the frontend app or external B. Build
and serve the frontend separately from the source checkout.

[legacy-usage.md](legacy-usage.md) archives the original root README with eleven
links repaired for its new directory. Public historical evidence sanitizes personal
transport paths; scientific data and conclusions remain unchanged. See
[public release provenance](public-release.md).
