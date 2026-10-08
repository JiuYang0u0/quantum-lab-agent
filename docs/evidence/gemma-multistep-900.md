# Gemma autonomous evaluation: authorized 900-second retry

2026-10-07. Exactly one new live run; four completion requests and three native tool
calls. Evaluator: **task_success=true**, **report_produced=true**.
Runtime termination: **completed**. Elapsed: **339.843 seconds**.
Run ID: `571a1f5575744f2e9d86c7b3a63753a6`.

## Conditions and exact change

Source A was clean on `feat/agent-foundation` at
`20c29fce839b56769d4a3b85d5223e2d175534c7`. Source B was clean at
`515aa81e92a19705a59e18dcc6806cbc600dd328` and used read-only through its existing
environment, with bytecode writes disabled and all runtime data outside B.

The user explicitly authorized this extended-timeout retry with reasoning enabled.
Model: `google/gemma-4-e2b`, LM Studio `http://127.0.0.1:1234/v1`, temperature 0,
1024 max tokens, six model steps, four-tool budget. Prompt equality against the
previous attempt-2 trace was checked exactly. Task: repetition d=3, rounds=1,
p=0.03, seed=42, shots=64/16/32; MLP one epoch with remaining CPU defaults.
No fallback, model change, manual IDs, or subsequent live attempt.

Only timeout configuration changed:

- Both evaluation scripts now accept 180–900 seconds instead of 180–300;
  their default remains 300.
- Multistep subprocess timeout is `args.seconds + 60` instead of 360 seconds:
  960 seconds for this run, still 360 for a 300-second run.
- Actual agent total deadline: 900 rather than 300 seconds.
- Provider already wraps each request with the remaining total budget in both
  `asyncio.timeout(remaining)` and HTTPX `timeout=remaining`; no provider edit needed.
- B polling requests retain their existing 30-second per-request cap within the
  total deadline. Shell timeout was 1,100,000 milliseconds.

## Independent outcomes and limitation

The post-run evaluator was rerun on the saved trace and confirmed the valid
sample → train → compare ID chain and exact task/training contract, with no tool
errors. The complete grounded numeric report is a deterministic rendering of
the comparison tool response, saved in `gemma-multistep-900-report.txt`.

The final model completion has **finish_reason=length** and its prose table is
truncated. The evaluator records `completion_token_limit`. Runtime `completed`
means the final response had no tool calls; it does **not** mean a natural stop
finish reason or a complete model-authored narrative. Task success here is the
evaluator's artifact-chain/report result, not an assertion that truncation vanished.

## IDs and numerical evidence

- Dataset: `dataset-bfee119b4d854d73b2c8bcb09d7aab2a`
- Checkpoint: `checkpoint-acf02fff0bd54c659aa0183cdd6cf791`
- Comparison/report: `comparison-760158bcf0354b7980a2b8679f0c9217`
- Sample job: `job-f045bfd7cd0f45deb93c4b899139baed` — succeeded
- Train job: `job-0e5358b3e58a4729b1bbbd940f4235d1` — succeeded
- Compare job: `job-6412055a658a444c910a08cf09f510ac` — succeeded

Each source below is a fragment of the comparison/report ID above.

| Decoder | Errors/shots | LER | CI | Decode seconds | Source |
|---|---:|---:|---|---:|---|
| MWPM | 0/32 | 0 | [0, 0.107182715057] | 0.000314400065690279 | `#prediction_0` |
| Lookup | 0/32 | 0 | [0, 0.107182715057] | 0.00004409998655319214 | `#prediction_1` |
| MLP | 3/32 | 0.09375 | [0.0324009626263, 0.242184993358] | 0.0005232000257819891 | `#prediction_2` |

This tiny fixed-shot evaluation is a smoke test, not decoder superiority evidence.

| Step | Finish reason | Prompt tokens | Completion tokens | Reasoning token count | Seconds |
|---|---|---:|---:|---:|---:|
| 1 | tool_calls | 739 | 892 | 826 | 63.125 |
| 2 | tool_calls | 895 | 594 | 535 | 42.969 |
| 3 | tool_calls | 1045 | 406 | 326 | 37.625 |
| 4 | length | 3328 | 1024 | 652 | 187.485 |

Completion time total: 331.204 seconds. Tool call/result times relative to trace
creation: sample 63.185/67.624s; train 110.624/114.156s; compare 151.827/152.229s.
Finish event: 339.762s; total including assessment/export preparation: 339.843s.
Only numeric reasoning-token usage is retained, not reasoning text.

## Comparison with the previous 300-second run

| Measure | Previous attempt 2 (300s) | This authorized run (900s) |
|---|---|---|
| Task success / report produced | false / false | true / true |
| Termination | time_budget | completed |
| Completions | 2 | 4 |
| Completion time | 265.312s | 331.204s |
| Artifact progress | Sample; training last observed running | Sample, checkpoint, comparison |
| Final completion finish reason | tool_calls | length |

The comparison report arrived at 152.229s in this run, before even the old 300s
deadline, while the final response extended past it. The first two completions
were also much faster (106.094s versus 265.312s). Thus the larger deadline allowed
this run to finish but this is not a controlled demonstration that timeout alone
caused the improvement. Original evidence and its historical conclusions remain
unchanged; this document records the newly authorized run.

## Evidence, cleanup, and checks

Committed files in `docs/evidence/`:

- `gemma-multistep-900-trace.json`: sanitized trace, timestamps, calls, tool results.
- `gemma-multistep-900-summary.json`: outcomes, settings, timings, usage, numeric provenance.
- `gemma-multistep-900-assessment.json`: independently rerun evaluator output.
- `gemma-multistep-900-report.txt`: complete tool-grounded report.

Original SQLite and exports: `.qla/gemma-multistep-900/`.
Retained B artifacts/jobs/log: `C:\Users\PUBLIC_USER\AppData\Local\Temp\opencode\qla-b-7r8cf7jw\`.
Launcher output: `C:\Users\PUBLIC_USER\AppData\Local\Temp\opencode\gemma-multistep-900-launch.log`.
The launcher stopped its own process tree (PIDs 21256, 41564, 16592); port 18000
was verified free afterward. No unrelated server was reused or stopped.

Verification: `python -m pytest -q` — 57 passed in 4.95s;
`ruff check .` — all checks passed. No KB edits or push.

Invocation (already executed once; do not rerun without authorization):

```powershell
.\.venv\Scripts\python.exe scripts/isolated_eval.py --b-repo C:\Users\PUBLIC_USER\Personal\20-Projects\neural-qec-complete --multistep --output .qla/gemma-multistep-900 --max-tokens 1024 --max-steps 6 --seconds 900
```
