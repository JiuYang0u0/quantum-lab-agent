# QEC offline binding assessment v2

The review2b87c5b follow-up adds `qec_evidence.assess_bound_qec` as a separate,
versioned acceptance gate. `evaluation.assess` remains the legacy scientific
assessment so archived assessments can still be reproduced exactly. It is not
sufficient by itself for native/job provenance acceptance. A3 `verify.py` now
requires both gates before printing PASS. Original traces, summaries, reports,
artifacts and historical assessments are preserved.

The bounded contract is one sample → train → compare chain, optionally followed
by one read of that exact report. It checks unique native IDs; serial ordered
native/executed calls; normalized arguments; intent arguments when present;
every job poll's request, kind, ID and status; terminal success and artifact ID;
sample/train result job IDs and success; dataset/checkpoint/report lineage;
comparison benchmark defaults and report circuit/sampling parameters. Missing,
orphaned, duplicated, reordered and incomplete chains fail closed. Batched native
calls use the same serial queue contract.

Inspection of the actual archive confirms that job events are bare B job objects,
not HTTP wrappers. Sample/train results contain `job_id`, `artifact_id`, `status`.
Compare returns the fetched report, without a job ID or status; its artifact must
match the successful compare job. The expected POST endpoint is derived from
the tool (`/api/jobs/sample`, `/api/jobs/train`, `/api/jobs/compare`) and matched
to the job kind. **The archive has no HTTP URL or submission-response evidence**;
this gate cannot independently prove which URL was contacted. Endpoint fields in
the new assessment describe expected adapter routing, not captured wire evidence.

Tool schema defaults normalize omitted versus explicit scientific defaults.
The service's four additional circuit noise overrides are accepted only when
explicitly null (the archived default); non-null overrides are rejected rather
than silently discarded. No arbitrary service request fields are dropped.

The Bell five-call pairing, resource circuit binding, scoped `analyze` projection,
and transparent historical strict `unique_case_chain` failure are unchanged.

Regression coverage uses actual archived wrappers, including both original
full-verifier probes: changing only native training dataset, and changing every
training job request dataset while leaving native/executed calls unchanged.
Both must raise before PASS. Further mutations cover all three parameter layers,
sample/train/compare jobs, result IDs/status, lineage, serial integrity, and
default normalization. Offline validation: 235 tests passed (42 new), Ruff and
frontend production build passed; A2 archived hash/reassessment test and A3 full
verifier included. Independent review gate must rerun after this fix.

All five older QEC archives were also reassessed against the pre-fix evaluator:
outputs are identical to that baseline. Three reproduce every published
assessment field. The two original Gemma attempts already differ from their
published summaries in `tool_calls` (both) and `jobs` (attempt 2); this pre-existing
difference is retained transparently, not repaired by rewriting history. All
historical JSON/report/image evidence content was compared with the Git baseline
and is unchanged (text comparisons allow checkout line-ending normalization).
