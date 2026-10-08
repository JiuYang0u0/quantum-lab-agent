# Observed results

These are historical smoke evaluations, **not controlled benchmarks**, broad
reliability estimates, QPU results, or comparative model rankings.

## NVIDIA Web acceptance (2026-10-09)

Exact recorded model: `deepseek-ai/deepseek-v4.1-flash`; temperature 0,
2048 output-token limit; one attempt per case, no retries/fallback/interpretation.

| Case | Completions / tools | Submit-to-finish seconds | Outcome |
|---|---:|---:|---|
| Bell ideal | 4 / 5 | 43.222 | `completed`; scoped scientific checks pass |
| QEC sample/train/compare | 3 / 3 | 43.904 | `report_ready`; verified report goal |

Total **7 completions** of an approved 10-call budget. Agent-only durations were
40.149 and 43.843 seconds. Bell used 1024 shots, seed 7, counts 00:527/11:497,
premeasurement fidelity 1.0. QEC used 32 test shots: MWPM and lookup 0 errors,
MLP 3 errors. Zero observed errors is not zero true error probability (upper
recorded interval approximately .1072). See the
[full Web evidence and real screenshots](evidence/a3-nvidia-web-20261009/README.md)
and [scope explanation](evaluation.md).

## Other retained observations

- [NVIDIA A2](evidence/a2-nvidia-20261008.md): Bell 70.531 seconds/4 calls;
  noisy GHZ3 164.406 seconds/5 calls; 9 calls total. Simulation fidelity 1.0 and
  .926984 respectively. These timings cannot establish a Web speedup: runs and
  workflows differ and were not controlled comparisons.
- [Gemma attempts](evidence/gemma-multistep.md): nested-argument failure, followed
  by sample/ID propagation but timeout without a comparison report.
- [900-second Gemma run](evidence/gemma-multistep-900.md): scientific task/report
  succeeded in 339.843 seconds, four completions; final model prose was truncated
  (`finish_reason=length`), not a natural model stop.
- [Gemma finalization attempt](evidence/gemma-finalize-report-900.md): failed
  before any tool, one 1024-token completion with empty content and `length`;
  no report or job. It cannot demonstrate a live finalization speedup.
- [Offline finalization replay](evidence/finalization-offline.md): 4 → 3 model
  completions in a recorded fixture, not a new live run or measured speedup.
- [Early probes](evidence/README.md): initial timeouts/empty output and later
  512-token tool-call success are both retained. Early records lack metadata
  needed to conclude whether token truncation caused empty output.

No new provider calls were made for local 0.1.0 packaging. The
[release-readiness record](release-readiness.md) separates local checks from
authored but unexecuted hosted CI.
