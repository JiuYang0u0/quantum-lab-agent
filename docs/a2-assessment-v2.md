# A2 offline assessment version 2

Version 2 adds `assessment_version: 2` and five acceptance criteria:
`unique_case_chain`, `build_request_binding`, `verify_request_binding`,
`simulation_request_binding`, and `read_request_binding`.

The historical evaluation at `f3ae643` checked native arguments against execution
arguments but did not bind those arguments to returned artifacts. Mutating both
argument copies together could therefore incorrectly pass. Version 2 fixes that
offline acceptance defect; it does not change runtime termination policies.

Native call IDs must be nonempty and unique. Since the original execution events
have no call IDs, correlation requires an ordered native-call queue and exactly
one same-name result per execution before another execution or model turn.
Duplicate, orphaned, reordered, incomplete and ambiguous chains are rejected.
Batched native calls (including the real Bell verify/simulate batch) are supported.
These two case definitions require exactly one build → verify → simulate → read
chain; extra tool chains require a separate evaluator definition.

Requests are normalized with the project's tool schemas. Build arguments must
match the saved BuildCircuit specification, including preset or explicit gates;
omitted defaults and explicit defaults are equivalent. A preset and an explicit
gate list are distinct content-addressed specifications, even if their unitaries
are equivalent. Verify and simulation must reference the built artifact; the
verify result must match its verification evidence. Simulation arguments must
match the stored normalized configuration (including shots, seed and noise).
Read arguments must reference the loaded simulation artifact. Existing loader
hash validation and independent scientific checks remain in effect.

The original archive, summary assessment shape, manifests, hashes and live
evidence documents are preserved without rewriting. The archive records the
historical 13-check assessment. Version 2 has 18 criteria on successful cases;
its offline reassessment is covered by `test_archived_traces_and_hashes_unchanged`.
Both historical cases pass the stricter checks. No additional provider calls are
needed or authorized for this fix.
