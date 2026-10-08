"""Local scientific operations, invoked on a worker thread by the adapter."""
import asyncio
import io
import threading
import time
from importlib.metadata import version

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, state_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

from .quantum_store import QuantumStore
from .quantum_types import QUANTUM_TOOLS, TARGET_THRESHOLD, BuildCircuit

PLOT_LOCK = threading.Lock()
BASIS = ["rz", "sx", "x", "cx"]


def provenance():
    return {"schema_version": 1, "versions": {p: version(p) for p in ("qiskit", "qiskit-aer", "numpy")},
            "target_definition": "independent analytic vector: (|0...0> + |1...1>)/sqrt(2)",
            "bit_order": "q[n-1]...q[0]; q0 least significant", "threshold": TARGET_THRESHOLD}


def circuit(spec):
    qc = QuantumCircuit(spec.qubits)
    if spec.preset:
        qc.h(0)
        for q in range(1, spec.qubits):
            qc.cx(0, q)
    else:
        for gate in spec.gates:
            args = ([] if gate.angle is None else [gate.angle]) + gate.qubits
            getattr(qc, gate.name)(*args)
    return qc


def target_vector(qubits):
    target = np.zeros(2**qubits, dtype=complex)
    target[0] = target[-1] = 1 / np.sqrt(2)
    return target


def verification(qc):
    fidelity = float(state_fidelity(Statevector.from_instruction(qc), target_vector(qc.num_qubits)))
    return {"status": "verified" if fidelity >= TARGET_THRESHOLD else "target_mismatch",
            "ideal_premeasurement_fidelity": fidelity, "threshold": TARGET_THRESHOLD}


def resources(qc):
    compiled = transpile(qc, basis_gates=BASIS, optimization_level=0, seed_transpiler=7)
    return {"basis_gates": BASIS, "optimization_level": 0, "seed_transpiler": 7,
            "connectivity": "all-to-all; no routing or hardware durations",
            "measurements_included": False, "depth": compiled.depth(),
            "gate_counts": dict(compiled.count_ops()),
            "two_qubit_gates": sum(i.operation.num_qubits == 2 for i in compiled.data),
            "density_matrix_bytes": 16 * 4**qc.num_qubits}


def render_quantum_report(report):
    import hashlib

    from .quantum_store import canonical
    payload = {k: v for k, v in report.items() if k not in ("artifact_id", "rendered")}
    if (report.get("kind") != "quantum_simulation"
            or hashlib.sha256(canonical(payload)).hexdigest() != report.get("artifact_id")):
        raise ValueError("invalid quantum simulation fingerprint/type")
    return (f"Quantum simulation [{report['artifact_id']}]\n"
            f"Circuit [{report['circuit_id']}] target={report['target']}\n"
            f"Ideal verification: {report['verification']['status']}\n"
            f"Premeasurement fidelity: {report['premeasurement_fidelity']:.12g}\n"
            f"Counts ({report['config']['shots']} shots): {dict(sorted(report['counts'].items()))}\n"
            "Fidelity is computed from the premeasurement density matrix, not inferred from counts.")


class QuantumAdapter:
    def __init__(self, root):
        self.store = QuantumStore(root)
        self.target = None
        self.attempts = 0
        self.circuit_verifications = {}
        self.relevant_circuits = set()
        self.draft_circuit = None

    @property
    def has_target_mismatch(self):
        relevant = self.relevant_circuits | ({self.draft_circuit} if self.draft_circuit else set())
        return any(self.circuit_verifications[c]["status"] == "target_mismatch"
                   for c in relevant)

    async def execute(self, name, arguments, deadline):
        if name not in QUANTUM_TOOLS:
            raise ValueError("tool not in quantum family")
        args = QUANTUM_TOOLS[name][0].model_validate(arguments)
        if name == "build_circuit":
            binding = (args.target, args.qubits)
            if self.target is not None and self.target != binding:
                raise ValueError("target is locked for this run")
            if self.attempts >= 3:
                raise ValueError("three build attempts exhausted")
            self.target = binding
            self.attempts += 1
        async with asyncio.timeout(max(0, deadline - time.monotonic())):
            result, identity, evidence = await asyncio.to_thread(self.work_with_evidence, name, args)
        self.circuit_verifications[identity] = evidence
        if name == "build_circuit":
            self.draft_circuit = identity
        else:
            self.relevant_circuits.add(identity)
        return result

    def work_with_evidence(self, name, args):
        """Bind successful tool use to freshly computed ideal circuit evidence.

        Draft builds can be repaired. Once a circuit is consumed by another tool,
        its correctness remains relevant even when a different circuit is built.
        Keep this state update outside the worker so timed-out work cannot publish it.
        """
        result = self.work(name, args)
        if name == "build_circuit":
            identity = result["artifact_id"]
        elif name in ("plot", "quantum_read_report"):
            identity = self.store.get(args.result_id, "quantum_simulation")["circuit_id"]
        else:
            identity = args.circuit_id
        _, qc = self.load_circuit(identity)
        return result, identity, verification(qc)

    def load_circuit(self, identity):
        item = self.store.get(identity, "quantum_circuit")
        spec = BuildCircuit.model_validate(item["spec"])
        if self.target is not None and self.target != (spec.target, spec.qubits):
            raise ValueError("artifact target differs from locked target")
        return spec, circuit(spec)

    def work(self, name, args):
        if name == "build_circuit":
            return self.store.put({"kind": "quantum_circuit", "spec": args.model_dump(),
                                   "verification": verification(circuit(args)), **provenance()})
        if name in ("plot", "quantum_read_report"):
            report = self.store.get(args.result_id, "quantum_simulation")
            self.load_circuit(report["circuit_id"])
            if name == "quantum_read_report":
                return {**report, "rendered": render_quantum_report(report)}
            return self.plots(report)
        spec, qc = self.load_circuit(args.circuit_id)
        if name == "verify":
            return {"circuit_id": args.circuit_id, **verification(qc)}
        if name == "analyze":
            return {"circuit_id": args.circuit_id, **resources(qc)}
        noise = NoiseModel()
        for arity, p, names in [(1, args.noise.depolarizing_1q,
                                ["h", "x", "y", "z", "s", "sdg", "rx", "ry", "rz"]),
                               (2, args.noise.depolarizing_2q, ["cx", "cz"])]:
            if p:
                noise.add_all_qubit_quantum_error(depolarizing_error(p, arity), names)
        r = args.noise.readout
        if r:
            noise.add_all_qubit_readout_error(ReadoutError([[1-r, r], [r, 1-r]]))
        backend = AerSimulator(method="density_matrix", noise_model=noise,
                               max_parallel_threads=1, max_memory_mb=64)
        measured = qc.copy()
        measured.save_density_matrix(label="premeasurement")
        measured.measure_all()
        result = backend.run(measured, shots=args.shots, seed_simulator=args.seed).result()
        if not result.success:
            raise ValueError("Aer simulation failed")
        rho = result.data(0)["premeasurement"].data
        fidelity = float(state_fidelity(rho, target_vector(spec.qubits)))
        return self.store.put({"kind": "quantum_simulation", **provenance(),
                               "circuit_id": args.circuit_id, "target": spec.target,
                               "config": args.model_dump(), "verification": verification(qc),
                               "premeasurement_fidelity": fidelity,
                               "density_matrix": {"real": rho.real.tolist(), "imag": rho.imag.tolist()},
                               "counts": result.get_counts(), "resources": resources(qc),
                               "noise_semantics": "Depolarization after each declared 1q/2q gate; no optimization. Readout is symmetric independent classical bit flip only."})

    def plots(self, report):
        with PLOT_LOCK:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from qiskit.visualization import plot_histogram
            _, qc = self.load_circuit(report["circuit_id"])
            figures = {"circuit": qc.draw(output="mpl"),
                       "histogram": plot_histogram(report["counts"])}
            graphics = {}
            try:
                for label, figure in figures.items():
                    for extension in ("svg", "png"):
                        buffer = io.BytesIO()
                        figure.savefig(buffer, format=extension, bbox_inches="tight")
                        graphics[f"{label}_{extension}"] = self.store.graphic(buffer.getvalue(), extension)
            finally:
                for figure in figures.values():
                    plt.close(figure)
            return self.store.put({"kind": "quantum_plots", "result_id": report["artifact_id"],
                                   "graphics": graphics, **provenance()})
