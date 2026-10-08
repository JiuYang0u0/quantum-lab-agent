# Architecture

This is a **classical LLM orchestrator**, not a quantum LLM or quantum-trained
language model. A conventional model selects bounded, typed tools. Qiskit/Aer
simulates small quantum circuits on a classical CPU; external B performs QEC work.

```text
React UI -> local FastAPI -> Agent -> OpenAI-compatible model
CLI ----------------------> Agent -> selected tool family
                                      | quantum: local Qiskit/Aer + hash store
                                      | qec: HTTP -> external Project B
                              Trace SQLite -> deterministic report/export
```

| Layer | Source and responsibility |
|---|---|
| Entrypoints | [cli.py](../src/quantum_lab_agent/cli.py), [workbench.py](../src/quantum_lab_agent/workbench.py): budgets and request validation |
| Model | [provider.py](../src/quantum_lab_agent/provider.py): native OpenAI-compatible calls, metadata, no automatic retries |
| Orchestration | [runtime.py](../src/quantum_lab_agent/runtime.py): Agent, Trace, Limits, Finalization, QEC adapter, replay |
| QEC contracts | [schemas.py](../src/quantum_lab_agent/schemas.py), [qec_evidence.py](../src/quantum_lab_agent/qec_evidence.py) |
| Quantum | [quantum.py](../src/quantum_lab_agent/quantum.py), [quantum_types.py](../src/quantum_lab_agent/quantum_types.py), [quantum_store.py](../src/quantum_lab_agent/quantum_store.py) |
| Scientific assessment | [evaluation.py](../src/quantum_lab_agent/evaluation.py), [quantum_evaluation.py](../src/quantum_lab_agent/quantum_evaluation.py) |
| Fixture | [workbench_fixture.py](../src/quantum_lab_agent/workbench_fixture.py): injected model and closed mock HTTP transport |
| UI | [App.tsx](../frontend/src/App.tsx), [Evidence.tsx](../frontend/src/Evidence.tsx), [toolTiming.ts](../frontend/src/toolTiming.ts) |

The model cannot switch tool families or run shell/Python/QASM. Final numeric
answers come from tool evidence via deterministic rendering, not model prose.
SQLite persists trace events and QEC POST intents. Web request IDs bind to a
canonical request digest; they do not provide global B-side exactly-once behavior.
Artifact hashes check integrity, not publisher identity or digital signatures.

The workbench is a loopback-only, single-user service without user authentication.
Only run-authorized, hash-checked graphic files are served. See
[API](api-reference.md), [configuration](configuration.md), and [limitations](limitations.md).
