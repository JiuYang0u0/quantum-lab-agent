# NVIDIA configured native-tool evaluation

One authorized invocation succeeded with the exact locally configured model
`deepseek-ai/deepseek-v4.1-flash`, NVIDIA endpoint
`https://integrate.api.nvidia.com/v1`, temperature 0, and 2048 output tokens.
Project `.env` was loaded without overriding existing process environment variables.
No extra model-specific thinking arguments were supplied.

## Provenance and bounds

- A starting revision: `b312bf2b300b4ad73a7910c56bcfc816b857634b`, clean,
  branch `feat/agent-foundation`; evaluated with the script changes in this commit.
- B revision: `515aa81e92a19705a59e18dcc6806cbc600dd328`, branch
  `security/public-release`, clean before and after; no B changes.
- Python 3.12.13, Windows 11 build 26200, httpx 0.28.1, pydantic 2.13.5,
  python-dotenv 1.2.4. Existing B virtual environment used read-only with bytecode disabled.
- Probe: at most two completions within 180 seconds. Task: at most six
  completions, four tools, 900 seconds, finalization reports=1, interpret=false.
- Five actual completions overall; no retries, fallback, model switch, injected
  artifact IDs, or interpretation. Tools were selected through native model calls.
- Exact task prompt equality with `gemma-multistep-900-trace.json` verified offline:
  repetition d=3, rounds=1, p=.03, seed=42, shots 64/16/32; MLP one epoch,
  remaining training defaults; same dataset/checkpoint against MWPM and lookup.

## Results

Probe succeeded (`roundtrip_received`): two completions, one list-artifacts tool,
49.640 seconds. Completion times 26.422/23.078 seconds; finish reasons
`tool_calls`/`stop`; total tokens 373/423.

Task run `79bf8d4f0f174bad85bb0c74fa532d04`: task_success=true,
report_produced=true, termination=`report_ready`, source=`policy`,
task_completion=`verified_report_goal`, interpretation=`not_requested`.
Three completions, three tool calls, three successful jobs; no tool errors.
Elapsed task time 47.437 seconds; provider time 42.546 seconds. All three
finish reasons were `tool_calls`; policy finalization did not require a natural model stop.
Completion times: 16.718/14.000/11.828 seconds. Prompt tokens: 1766/1959/2128;
completion tokens: 132/106/117; total tokens: 1898/2065/2245.
Combined probe plus task elapsed: 97.077 seconds, excluding server startup/cleanup.

| Artifact | Actual ID |
|---|---|
| Dataset | `dataset-e90420d6632542c1b99b43476b717dd8` |
| Checkpoint | `checkpoint-839667acfaa94277a1b9ab3f0f1da3c8` |
| Comparison | `comparison-a544c324a208420a8a19b226336bbad0` |

Jobs: `job-50c342ee3f33433086d55f3108e7381f` (sample),
`job-da7a55aef5784606ac6038a5f9547657` (train),
`job-a7e5b0fd05484889ada87967ed7ab53c` (compare).

| Decoder | Errors/shots | LER | CI | Decode seconds |
|---|---:|---:|---|---:|
| MWPM | 0/32 | 0 | [0, 0.107182715057] | 0.000262800000201 |
| Lookup | 0/32 | 0 | [0, 0.107182715057] | 0.000033199999962 |
| MLP | 3/32 | 0.09375 | [0.0324009626263, 0.242184993358] | 0.000842800000100 |

Sources: comparison ID above, `prediction_0`, `prediction_1`, `prediction_2`
respectively. This fixed-shot smoke test is not decoder-superiority evidence.

## Qualified historical comparison

Prior successful Gemma run took 339.843 seconds with four completions and three
tools, with report arrival around 152.229 seconds and a final 187.485-second
completion. NVIDIA reached its verified report in 47.437 seconds with three
completions. The later Gemma finalization run instead failed at its first
1024-token completion after 104.656 seconds, producing no tools/report.
These are single observations with different hosted/local hardware, models,
token budgets (2048 versus 1024), cache conditions, and termination policies;
they do not establish a controlled speedup or reliability rate.

## Evidence, cleanup, checks

Adjacent `nvidia-configured-*` JSON files contain the sanitized probe, task trace,
summary, independently recomputed assessment, and B artifact metadata plus SHA256
hashes; report text is deterministic tool-grounded output. Numeric usage is retained,
reasoning text and credentials are excluded. Original traces/SQLite remain in
`.qla/nvidia-configured-20261008/`.

B artifacts and server log remain at
`C:\Users\PUBLIC_USER\AppData\Local\Temp\opencode\qla-b-2rdzoqjh\`.
Launcher output is retained in the harness shell log for
`sh_11b56f1cf001B6vvxJ78VJbSpS`. Owned PIDs 8388, 20660, and 20560 were
terminated, independently confirmed absent; port 18000 was independently bound
successfully after cleanup. B remains clean at its original revision.

Checks: 101 tests passed, Ruff passed, wheel and sdist built. Historical evaluation
script CLI defaults remain compatible; configured mode is explicit. No push or KB edits.

Invocation:

```powershell
.venv\Scripts\python.exe scripts/isolated_eval.py --configured --b-repo C:\Users\PUBLIC_USER\Personal\20-Projects\neural-qec-complete --output .qla/nvidia-configured-20261008 --max-steps 6 --seconds 900
```
