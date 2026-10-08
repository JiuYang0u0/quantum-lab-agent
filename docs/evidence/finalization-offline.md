# Report finalization — offline evidence

Source baseline: `be6b376`, branch `feat/agent-foundation`.

## Method and result

`tests/test_finalization.py::test_original_900_trace_replayed_with_fewer_provider_calls`
feeds the preserved model messages and tool results from
`gemma-multistep-900-trace.json` into the current runtime. Its adapter is replaced
with an offline recorded-result adapter; no model, QEC HTTP server or B process
is contacted. The original trace and assessment are not rewritten.

- Recorded original: four returned model completions.
- Explicit single-report goal: three calls; no finalization call after compare.
- Saved: one of four calls (25%). No claim about live elapsed-time savings.
- Full deterministic output equals `replay(original)` exactly.
- Original 900-second assessment still equals the preserved assessment JSON.
- Earlier attempt-one/attempt-two assessment/replay compatibility remains covered.

## Regression scope

The suite covers no extra provider call at report readiness; distinct-report counts
(including repeated reads); general-mode continuation; early model stop before the
declared count; empty/inconsistent reports; comparison dataset/checkpoint/decoder
contract mismatches; commentary length and timeout; rejected numeric claims;
report emission before commentary; dedicated request token budget; bounded settings;
secret redaction and visible numeric budget metadata; truthful policy vs model stop.

Optional interpretation is intentionally a selection among reviewed non-numeric
conceptual caveats. Free-form numeric interpretation is not enabled. Accepted
commentary is a separate labeled field; the report renderer is authoritative.

## Decisions to revisit with the user

- Whether a future named single-report CLI profile should enable policy stopping
  by default. General `run` remains model-led for compatibility and arbitrary goals.
- Whether richer declarative goals (specific datasets/noise/lineage) are needed
  beyond explicit distinct-report counts and comparison argument verification.
- Whether to authorize a new live run to measure latency; offline call savings do
  not predict provider reasoning or wall time.
- Whether useful free-form explanations justify a grounded claim validator.
  Current commentary only selects a reviewed conceptual caveat.
