# Tool reference

Authoritative strict Pydantic schemas:
[QEC](../src/quantum_lab_agent/schemas.py),
[Quantum](../src/quantum_lab_agent/quantum_types.py).
Extra fields, path-like IDs, invalid types, and out-of-bound parameters are rejected.

## Quantum family (standalone CPU)

| Tool | Arguments / result |
|---|---|
| `build_circuit` | Bell/GHZ target; preset or restricted gates; returns circuit SHA-256 |
| `verify` | `circuit_id`; independent ideal target fidelity and status |
| `analyze` | `circuit_id`; transpiled resource assumptions/counts |
| `run_simulation` | `circuit_id`, `mode`, `shots`, `seed`, `noise`; simulation hash, density-matrix fidelity, counts |
| `quantum_read_report` | `result_id`; deterministic report |
| `plot` | `result_id`; circuit/histogram SVG and PNG references |

2–6 qubits (Bell exactly 2), at most 64 gates. Gates:
`h/x/y/z/s/sdg/cx/cz/rx/ry/rz`; finite rotation angles. Shots 1–8192,
nonnegative 32-bit seed. Mode `ideal`/`noisy`; noise fields
`depolarizing_1q`, `depolarizing_2q`, `readout` range 0–1.
No arbitrary code or QASM. Agent allows at most three builds per run and locks
the initial target/qubit count. Ideal target threshold is 0.999999.

## QEC family (external B)

| Tool | B route / purpose |
|---|---|
| `qec_list_artifacts` | GET `/api/artifacts` |
| `qec_sample` | POST `/api/jobs/sample`, poll job, return dataset ID |
| `qec_train` | POST `/api/jobs/train`, poll job, return checkpoint ID |
| `qec_compare` | POST `/api/jobs/compare`, poll and read comparison |
| `qec_read_report` | GET `/api/results/{id}` |

Defaults are small CPU runs: train/validation/test 128/32/64, training one epoch,
hidden size 8, one thread. Preserved integration uses 64/16/32. A exposes simple
noise `p`, not B's four independent overrides. IDs must come from actual results;
duplicate checkpoints are rejected. Async job polling is runtime-controlled,
not another model task. Reports bind dataset/checkpoint IDs and decoder coverage.
See [QEC assessment](qec-assessment-v2.md) for the stronger acceptance gate.
