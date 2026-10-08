# A3 production NVIDIA Web acceptance — 2026-10-09

Both requested scientific tasks passed through the real browser UI and production
FastAPI factory at source `950afd8`. This is a two-case smoke acceptance, not a
reliability, performance, hardware, or container benchmark.

| Case | Run ID | UI status | Completions / tools | Submit-to-finish seconds |
|---|---|---|---|---|
| Bell | `3a1ddf7cb0794b049ba966c9913a948f` | `completed` | 4 / 5 | 43.222 |
| QEC | `ee0aed7c00234101989131000a72dd8f` | `report_ready` | 3 / 3 | 43.904 |

Exactly **7 of 10 approved completions** observed, one attempt per case; no retries,
fallback model, LM Studio calls, interpretation calls, or follow-up live attempts.
Each browser request selected its family explicitly and supplied `max_steps=5`,
`max_tools=5`, `seconds=300`, enforced by the server runtime. API global bounds
remain the production defaults; these are per-request limits, not a global quota.
Exact `.env` model: `deepseek-ai/deepseek-v4.1-flash`, NVIDIA API, 2048 output tokens,
temperature 0. Production `/api/config` returned `fixture=false`.

## Grounded findings

- Bell: ideal simulation, 1024 shots, seed 7; counts **00:527, 11:497**;
  reported premeasurement fidelity **1.0**. Independent density evolution agrees;
  ideal target fidelity is approximately 1. Resource analysis: depth 4,
  `rz:2, sx:1, cx:1`, one two-qubit gate, density matrix 256 bytes, no measurements
  in resource counts. Full artifact IDs and versions are in `summary.json`.
- QEC: repetition distance 3, rounds 1, p=.03, seed 42, splits 64/16/32,
  MLP one epoch with remaining CPU defaults. Existing QEC evaluator passes the
  complete sample → train → compare ID chain and numeric provenance.

| Decoder | Errors/shots | LER | CI | Decode seconds |
|---|---:|---:|---|---:|
| MWPM | 0/32 | 0 | [0, .1071827150573635] | .0005731999990530312 |
| lookup | 0/32 | 0 | [0, .1071827150573635] | .00011069999891333282 |
| MLP | 3/32 | .09375 | [.032400962626319516, .24218499335778831] | .0009201999964716379 |

Quantum runtime `completed` alone is unverified; its scientific success comes
from artifact checks. QEC ended by report-goal policy (`verified_report_goal`),
not a model stop. Finish reasons are Bell `tool_calls` ×3 then `stop`, QEC
`tool_calls` ×3. Full token counts, event timestamps, job IDs, and assessment
results are retained. Timings derive from persisted server timestamps and include
initialization in submit-to-finish; agent-only times are 40.149 and 43.843 seconds.

### Evaluator scope

The Bell model additionally invoked `analyze` to answer the requested resources.
The historical A2 evaluator requires exactly four tools, so its **unmodified
full-trace assessment fails `unique_case_chain`**. That result is retained, not
silently relabeled. `verify.py` first validates all five native/executed pairs and
the resource circuit binding, then projects only `analyze` out of an in-memory
copy and runs the existing scientific evaluator. Every scientific criterion
passes on this scoped four-tool chain. Original published trace remains complete
except model prose removal. No evaluator implementation was changed.

## Files and offline reproduction

Offline review follow-up: `verify.py` additionally requires the versioned QEC
native/execution/job binding gate documented in
[`qec-assessment-v2.md`](../../qec-assessment-v2.md). Historical assessments and
raw evidence remain intact; the old QEC assessment alone is not the current
acceptance gate. The Bell projection and historical strict failure remain intact.

From the repository root (no API/model requests):

```powershell
uv run python docs/evidence/a3-nvidia-web-20261009/verify.py
```

`*-trace.json` retains tool calls/results and completion metadata but omits model
prose. Reasoning text and credentials are absent. `*-report.md` is the production
Markdown export; both JSON and Markdown endpoints returned HTTP 200 for each run.
`*-browser.png` captures the production page, explicitly labeling model prose as
unverified separately from grounded results. `quantum-artifacts/` preserves hashed
circuit/simulation JSON. No plot was requested or generated; graphics list is
empty (the browser's counts bars are UI rendering, not exported plot artifacts).

For a separately approved live reproduction: use the README's production API/UI
commands, a fresh `QLA_WORKBENCH_ROOT`, NVIDIA profile and the configured exact
model, and set `QLA_QEC_URL=http://127.0.0.1:18000` before starting A. Launch B's
`qec_core.service.app:create_app --factory` from its existing environment with
fresh `QEC_ARTIFACT_ROOT`, `PYTHONPATH=<B>/src`, `PYTHONDONTWRITEBYTECODE=1` and
port 18000. In the UI select each explicit family, paste the exact prompt from
its trace, set 5/5/300, QEC report goal 1 (Quantum 0), and click Start once.
Never automatically retry a submission or consume the remaining quota.

## Isolation and cleanup

- A initial working tree clean, branch `feat/agent-foundation`, source `950afd8`.
- B read-only source: branch `security/public-release`, commit
  `515aa81e92a19705a59e18dcc6806cbc600dd328`; clean before and after.
- Existing fixture API PID 20756 (8100) and repo Vite PID 19744 (5174) were
  command-line verified before their process trees were stopped.
- Own isolated root: `%LOCALAPPDATA%/Temp/opencode/qla-nvidia-web-20261009`;
  production trace/artifacts, B artifacts and local logs remain there.
- Own process trees stopped: A parent 17904 / listener 9044 (8100), UI 20700 /
  esbuild 7012 (5174), B parent 18924 / listener 7568 / worker 18808 (18000).
- Named browser `qla-nvidia-web` closed. Final listener check: **8100, 5174,
  18000, 8101, 5175 all free**. No user LM Studio or unrelated Docker service
  was stopped. Actual B override was configured before Settings loading;
  URLs are redacted in Web exports, with the actual endpoint recorded in summary.

Evidence/documents only; no application behavior changes. Independent review is
left to the parent session. No `.env`, B source, KB data, or raw provider reasoning
is included; no push performed.

Final checks: offline `verify.py` passed; `uv run ruff check .` passed;
`uv run pytest -q`: **193 passed** (one existing Starlette/httpx deprecation
warning); `git diff --check` passed. No frontend implementation changed.
