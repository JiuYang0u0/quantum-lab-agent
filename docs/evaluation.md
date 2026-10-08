# Evaluation contract

Three different claims must remain separate:

1. **Fixture/regression success:** injected model/HTTP behavior tests runtime/UI;
   Aer checks still execute a real classical simulator.
2. **Scientific task success:** actual artifacts and ID chains satisfy the fixed
   evaluator contract, with numeric provenance checked.
3. **Termination:** model `completed`, policy `report_ready`, budget exhaustion,
   interruption, or failure. A model stop alone does not prove task success.

[evaluation.py](../src/quantum_lab_agent/evaluation.py) assesses QEC chains;
[quantum_evaluation.py](../src/quantum_lab_agent/quantum_evaluation.py) assesses
quantum cases. Current refinements are documented in
[QEC v2](qec-assessment-v2.md) and [Quantum v2](a2-assessment-v2.md).

QEC checks native call/execution/job binding, dataset/checkpoint/report identity,
expected decoder coverage, and numeric consistency. A does not independently
recompute B predictions or Wilson intervals. Bell/GHZ evaluation uses independent
target/density checks and hash-addressed artifacts, not model explanation.

The Web Bell run has five tools because it also analyzes resources. The unchanged
historical four-tool A2 evaluator fails `unique_case_chain` on the full trace.
The Web verifier checks all five native/executed pairs and resource binding,
then removes only `analyze` from an in-memory copy for scoped scientific checks.
It does not rewrite the trace or claim the original strict assessment passed.

See [results](results.md) for measured cases and [limitations](limitations.md)
for what these checks cannot establish.
