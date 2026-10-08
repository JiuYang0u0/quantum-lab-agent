# Limitations

- Classical model orchestration and classical CPU simulation only: no quantum
  LLM, remote QPU, arbitrary code execution, RAG, or private knowledge-base dependency.
- Quantum supports restricted 2–6-qubit Bell/GHZ-target circuits, not arbitrary
  algorithms. QEC requires separately installed external Project B over HTTP.
- Fixture mode uses a fixed fake planner and mock QEC results. It ignores prompt
  semantics and is not live Agent evidence.
- Counts do not establish quantum fidelity. Fidelity is computed from the
  premeasurement density matrix against an independent target. Symmetric
  classical readout flips affect counts only. Gate depolarization uses
  `E(rho)=(1-p)rho+p I/2^n` after original gates; it is not a calibrated device model.
- Low noisy fidelity does not mean the ideal circuit was built incorrectly.
  Ideal target verification and noisy simulation fidelity are distinct.
- Resource counts use transpilation to rz/sx/x/cx, optimization level 0, seed 7,
  all-to-all connectivity, no measurements/routing/durations. They are not hardware
  execution cost predictions. Memory estimates exclude Python/plotting overhead.
- A verifies report consistency/binding, not every natural-language goal or all
  B calculations. Small samples and one-epoch training cannot rank decoders reliably.
- `completed` is not scientific success. Live smoke cases do not establish a
  success rate or performance benchmark. Provider availability/behavior can change.
- Workbench is local, unauthenticated, single-worker/single-instance. No cancel
  API, automatic cross-run resume, or server-side B idempotency guarantee.
  Uncertain POSTs are not retried; new runs can submit new work.
- Timeouts cannot forcibly cancel already running CPU work or external B jobs.
  Trace redaction is not a guarantee of privacy for arbitrary user data.
- Hashes detect byte corruption, not malicious replacement by a trusted local
  operator. Plot hashes may change across rerenders because of metadata.

See [scientific definitions](a2-quantum.md), [evaluation](evaluation.md), and
[security scope](../SECURITY.md).
