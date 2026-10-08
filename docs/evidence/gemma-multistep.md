# Gemma autonomous multi-step evaluation — 2026-10-07

**Task success: false. Grounded comparison report produced: false.**
Four live completions total across two runs; no model switch, fallback, manual ID injection,
or scripted sample/train/compare submission. Offline fixtures are separate synthetic tests.

Both runs used `google/gemma-4-e2b` at LM Studio `127.0.0.1:1234`, native tool calls,
temperature 0, 1024 max tokens per completion, max 6 model steps, max 4 tools,
and a 300-second run deadline. The task/prompt and success criteria were identical.
The task requires repetition distance 3, rounds 1, p=0.03, seed 42, 64/16/32 shots,
MLP training for one epoch, and comparison with the returned checkpoint plus MWPM/lookup.

## Attempts

| Attempt | Run ID | Completions | Termination | Outcome |
|---|---|---:|---|---|
| 1 | `ce1710916ce644fe8fee2b3744c212ce` | 2 | `completed_with_errors` | Invalid nested arguments; no B job |
| 2 | `6d0274702e894581b10c97025a456019` | 2 | `time_budget` | Sample succeeded; correct dataset ID passed to train; training still running at deadline |

Attempt 1 supplied strings instead of objects for `circuit` and `sampling`. Local strict
validation rejected them. The model stopped rather than correcting the call. Its completion
finish reasons were `tool_calls`, `stop`, not `length`. This is a schema-conformance failure,
not evidence of absent native-tool capability or token truncation.

The minimal repair expanded Pydantic local `$ref` definitions inline in tool schemas,
without changing validation constraints. Hypothesis: native chat-template rendering did not
expose referenced nested fields adequately. The earlier successful sample-only probe used
empty arguments and therefore did not test this. Attempt 2 then generated valid objects;
this supports the repair but does not establish the server template's internal behavior.

Attempt 2 spent 155.265 + 110.047 = 265.312 seconds in two completions.
Sample completed, and Gemma autonomously selected training with the exact returned ID:

- Dataset: `dataset-5b26e6307c1d4a86add261fa0828ecb3`
- Sample job: `job-3215a3de5b764aadb4cd26786552207b` (succeeded)
- Train job: `job-d1cf6b8c40cf4f8f9495cb4c5449acdc` (last observed running)
- Checkpoint and comparison: none observed by agent; no numerical comparison provenance.

The isolated server tree was stopped after the deadline, including its owned worker.
Training completion is **not** claimed. No third live run was attempted: increasing the
deadline or changing the task to claim success would not satisfy this bounded evaluation.

| Attempt/step | Finish reason | Prompt tokens | Completion tokens | Reasoning token count | Seconds |
|---|---|---:|---:|---:|---:|
| 1/1 | tool_calls | 513 | 953 | 887 | 69.875 |
| 1/2 | stop | 601 | 780 | 720 | 119.250 |
| 2/1 | tool_calls | 739 | 854 | 795 | 155.265 |
| 2/2 | tool_calls | 891 | 583 | 523 | 110.047 |

## Evidence and interpretation

`gemma-multistep-attempt-{1,2}-trace.json` and `-summary.json` preserve the original exports.
`-assessment.json` adds post-run step-to-tool and latest-job-state indexing. No reasoning
text is retained. `-report.txt` is the runtime's tool-evidence output, **not a comparison
report** in these failed runs. Attempt 1 contains no verified tool evidence; attempt 2
contains only the successful sample result.

The evaluator distinguishes `task_success`, `report_produced`, and `termination_status`.
A valid artifact chain can finish at `step_budget` with task success true; that is tested
offline and does not mean the model voluntarily stopped. Conversely, `completed` can
still have task success false. A report alone does not prove the requested ID chain.

Attempt 1 classifications: tool/evidence error, incomplete artifact chain, no grounded report.
Attempt 2 classifications: time budget, incomplete artifact chain, no grounded report.

## Reproduce

```powershell
uv run python scripts/isolated_eval.py --b-repo C:\Users\PUBLIC_USER\Personal\20-Projects\neural-qec-complete --multistep --output .qla/multistep-new-run --max-tokens 1024 --max-steps 6 --seconds 300
```

Use a new output directory; existing evidence is never overwritten. One invocation allows
at most six completions and never retries a run. A nonzero exit code is expected on failure;
the launcher still terminates its owned B process tree. Port 18000 must be free.
LM Studio must already have the exact model available. No UI is launched.

Source B stayed on `security/public-release`, commit `515aa81`; only read to launch its
existing environment. Isolated artifact/log directories under `%LOCALAPPDATA%\Temp\opencode`:
`qla-b-wu9r65v2` (attempt 1), `qla-b-axs_njmo` (attempt 2). Original SQLite files remain
under `.qla/multistep-attempt-{1,2}`. Historical probe traces are unchanged.
