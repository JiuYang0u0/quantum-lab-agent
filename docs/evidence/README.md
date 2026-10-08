# Public evidence index

This directory preserves historical evidence, including failures. It is not a
collection of uniformly successful runs. Public copies additionally replace personal
Windows profile names with `PUBLIC_USER` in historical transport paths. These
placeholder paths are provenance, not portable instructions or required files.
Scientific numerical data, artifact bytes, historical assessments, and scientific
hashes are unchanged. Original unsanitized records remain in the private source;
public evidence is not claimed to be universally byte-identical to that source.
See [public release provenance](../public-release.md) for the mapping and checks.
New assessments supplement old ones rather than changing historical conclusions.

| Evidence | Meaning |
|---|---|
| [Web NVIDIA acceptance](a3-nvidia-web-20261009/README.md) | Two actual browser cases, real screenshots, seven calls, scoped Bell checks and QEC binding gate |
| [Web verifier](a3-nvidia-web-20261009/verify.py) | Offline verification of stored evidence; no model or B required |
| [A2 NVIDIA](a2-nvidia-20261008.md) | Bell/GHZ3 CLI smoke cases, nine calls, hashed simulation artifacts |
| [Configured NVIDIA](nvidia-configured.md) | Historical provider/QEC evaluation and provenance |
| [QEC integration](qec-integration.json) | Actual isolated external B CPU tool chain |
| [Gemma multistep failures](gemma-multistep.md) | Nested arguments and timeout, no successful complete report chain in these attempts |
| [Gemma 900-second attempt](gemma-multistep-900.md) | Retained longer-budget trace and assessment |
| [Gemma report-policy attempt](gemma-finalize-report-900.md) | Retained finalization-policy live evidence |
| [Offline finalization](finalization-offline.md) | Recorded fixture replay, not new live timing evidence |
| [Early diagnostic](model-diagnostic.json), [initial probe](lm-minimal-probe.json), [roundtrip](lm-tool-roundtrip.json) | Historical incomplete/failed capability diagnostics |
| [512-token probe](lm-minimal-probe-512.json), [sample Agent](lm-agent-sample-512.json) | Subsequent narrow native tool-call successes |

Interpret results using [evaluation](../evaluation.md), [results](../results.md),
[QEC v2](../qec-assessment-v2.md), and [Quantum v2](../a2-assessment-v2.md).
Run `uv run --locked python docs/evidence/a3-nvidia-web-20261009/verify.py`
from the repository root. Raw database/model logs are not distribution inputs.
