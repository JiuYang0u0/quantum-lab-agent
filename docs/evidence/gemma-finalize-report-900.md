# Gemma report-finalization: single authorized live run

Executed after approval of `a09e483` on `feat/agent-foundation`. **Task failed
before any tool call**: one completion exhausted its 1024-token limit, returned
empty content and no tool calls. No retry was performed.

## Configuration and provenance

- A source revision: `a09e483` (clean before execution).
- B source revision before and after: `515aa81e92a19705a59e18dcc6806cbc600dd328`,
  clean both times, branch `security/public-release`.
- Model: `google/gemma-4-e2b`, LM Studio `http://127.0.0.1:1234/v1`;
  existing provider temperature 0, max tokens 1024.
- Agent budget: 900 seconds, six completions maximum, four tools maximum.
- Explicit `--finalize-on-report`: trace confirms `reports=1`, `interpret=false`.
  Both evaluation scripts already supported this flag at the approved revision;
  no script or default changes were needed.
- Exact prompt equality with `gemma-multistep-900-trace.json` was asserted before
  launch and independently after execution. Original scientific request remains
  repetition d=3, rounds=1, p=0.03, seed=42, shots 64/16/32, MLP one epoch with
  remaining CPU defaults, then same-dataset/checkpoint comparison with MWPM/lookup.
- Exactly one live invocation, no fallback, model switch, injected IDs, or retry.

## Outcome, counts, and timings

Run ID: `472d85bd0cfa4b159045362a0259fac2`.

| Measure | Observed |
|---|---|
| Task success / report produced | false / false |
| Runtime termination | `no_tool_calls` |
| Termination source / task completion | `model` / `unverified` |
| Natural model stop observed | false |
| Report-ready event | absent |
| Interpretation | `not_requested`; no interpretation call |
| Completion requests / native tool calls / jobs | 1 / 0 / 0 |
| Completion time | 104.562 seconds |
| Total assessed elapsed | 104.656 seconds |
| Finish event relative to trace creation | 104.601 seconds |
| Finish reason | `length` |
| Prompt / completion / total tokens | 739 / 1024 / 1763 |
| Numeric reasoning-token usage | 1008 |

Dataset ID, checkpoint ID, comparison ID: **all null**. Job IDs: **none**.
Actual dataset/checkpoint lineage and decoder coverage are absent, not verified.
There is no comparison result or grounded report source. `report.txt` preserves
the runtime's `No verified tool evidence.` output. No reasoning text is present in the sanitized trace;
only numeric token usage is retained.

The independent evaluator classifies `completion_token_limit`, `no_tool_calls`,
`incomplete_or_invalid_artifact_chain`, and `no_grounded_report`. No tool errors
occurred because no tools were called. There was no extra completion after a
report, but this does **not** demonstrate live early finalization: the run never
reached its report goal. `termination_source=model` identifies the no-tool
response branch; it does not imply `finish_reason=stop`.

## Cautious comparison with the prior 900-second run

| Measure | Prior `gemma-multistep-900` | This run |
|---|---|---|
| Task success / report | true / true | false / false |
| Termination | `completed` | `no_tool_calls` |
| Completions / tools | 4 / 3 | 1 / 0 |
| Completion time total | 331.204s | 104.562s |
| Total elapsed | 339.843s | 104.656s |
| First completion finish reason | `tool_calls` | `length` |
| First completion token count | 892 | 1024 |
| Artifact progress | dataset, checkpoint, comparison | none |

The prior report arrived around 152.229s; a fourth completion then consumed
187.485s and ended at its token limit. This run cannot establish that the policy
saves that time: it failed during the first completion before policy finalization
could apply. These are single observations, not a causal or speed benchmark.
Historical evidence files were preserved without modification.

## Failure traceback and cleanup

The evaluator exited 1 for task failure. The launcher's `check=True` then raised
`subprocess.CalledProcessError` at `scripts/isolated_eval.py:63` (invoked from
line 74), after its `finally` cleanup. The full captured traceback and command
are retained in `gemma-finalize-report-900-launch.txt`; this is the launcher
reporting evaluator failure, not a separate model request or retry.

The isolated B server used port 18000 and the existing B environment read-only
with `PYTHONDONTWRITEBYTECODE=1`. Runtime storage and cwd were outside B:
`C:\Users\PUBLIC_USER\AppData\Local\Temp\opencode\qla-b-3gby9110\`.
Its retained server log records startup and the health request only. Owned PIDs
25832 and 26444 were terminated by the launcher; both were subsequently absent
and port 18000 was successfully bound in a cleanup check. All runtime artifacts
and logs were retained. B's Git revision and clean status were verified unchanged.

Original SQLite and exports: `.qla/gemma-finalize-report-900/`.
Original launcher log:
`C:\Users\PUBLIC_USER\AppData\Local\Temp\opencode\gemma-finalize-report-900-launch.log`.
Committed adjacent files: sanitized full trace, summary, independently rerun
assessment, report output, and UTF-8 launcher log including traceback.

Checks: `python -m pytest -q` — **95 passed in 7.28s**;
`ruff check .` — **all checks passed**; `uv build` — **sdist and wheel built**.
Independent saved-trace checks confirmed exact prompt, active one-report policy,
no interpretation, no tool/report-ready events, and the failed assessment.
No KB or B edits and no push.

Invocation (executed once; authorization consumed):

```powershell
.\.venv\Scripts\python.exe scripts/isolated_eval.py --b-repo C:\Users\PUBLIC_USER\Personal\20-Projects\neural-qec-complete --multistep --output .qla/gemma-finalize-report-900 --max-tokens 1024 --max-steps 6 --seconds 900 --finalize-on-report
```
