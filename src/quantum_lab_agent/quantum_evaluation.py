"""Offline A2 acceptance: bind native tool chains to hashed scientific artifacts."""
import itertools
import json

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from .quantum import circuit, render_quantum_report
from .quantum_store import QuantumStore
from .quantum_types import QUANTUM_TOOLS, BuildCircuit

CASES = {
    "bell_ideal": {"target": "bell", "qubits": 2, "mode": "ideal",
                   "noise": {"depolarizing_1q": 0.0, "depolarizing_2q": 0.0, "readout": 0.0}},
    "ghz3_gate_noise": {"target": "ghz", "qubits": 3, "mode": "noisy",
                        "noise": {"depolarizing_1q": 0.02, "depolarizing_2q": 0.04,
                                  "readout": 0.0}},
}


def independent_density(spec, noise):
    """Matrix evolution and explicit Pauli twirl; no Aer or adapter simulation call."""
    qc = circuit(spec)
    dim = 2**spec.qubits
    rho = np.zeros((dim, dim), complex)
    rho[0, 0] = 1
    for instruction in qc.data:
        indices = [qc.find_bit(q).index for q in instruction.qubits]
        step = QuantumCircuit(spec.qubits)
        step.append(instruction.operation, indices)
        unitary = Operator(step).data
        rho = unitary @ rho @ unitary.conj().T
        p = noise[f"depolarizing_{len(indices)}q"]
        if p:
            mixed = np.zeros_like(rho)
            for labels in itertools.product("ixyz", repeat=len(indices)):
                paulis = QuantumCircuit(spec.qubits)
                for label, index in zip(labels, indices, strict=True):
                    if label != "i":
                        getattr(paulis, label)(index)
                operator = Operator(paulis).data
                mixed += operator @ rho @ operator.conj().T / 4**len(indices)
            rho = (1-p)*rho + p*mixed
    return rho


def paired_execution(events):
    """Legacy traces lack execution IDs: require unambiguous serial event pairing.

    A model may issue several native calls together. Their unique IDs and order
    define a queue; each execution must have exactly one same-name result before
    the next execution or model turn. Metadata may appear between these events.
    """
    pending, pairs, seen_ids = [], [], set()
    active = None
    for event in events:
        kind, data = event["kind"], event["data"]
        if kind == "model":
            if pending or active is not None:
                raise ValueError("model turn before pending calls completed")
            for native in data.get("tool_calls", []):
                identity = native["id"]
                if not isinstance(identity, str) or not identity or identity in seen_ids:
                    raise ValueError("missing or duplicate native call ID")
                seen_ids.add(identity)
                name = native["function"]["name"]
                schema = QUANTUM_TOOLS[name][0]
                args = schema.model_validate(json.loads(native["function"]["arguments"]))
                pending.append((identity, name, args.model_dump()))
        elif kind == "tool_call":
            if active is not None or not pending:
                raise ValueError("ambiguous or unsolicited execution")
            identity, name, args = pending.pop(0)
            normalized = QUANTUM_TOOLS[data["tool"]][0].model_validate(data["args"]).model_dump()
            if name != data["tool"] or args != normalized:
                raise ValueError("native/executed call mismatch")
            active = (identity, name, normalized)
        elif kind == "tool_result":
            if active is None or active[1] != data["tool"]:
                raise ValueError("orphaned, reordered or wrong-name result")
            pairs.append((*active, data["result"]))
            active = None
        elif kind in ("tool_error", "finish") and (pending or active is not None):
            raise ValueError("incomplete executed call chain")
    if pending or active is not None or not pairs:
        raise ValueError("missing execution results")
    return pairs


def assess_quantum(export, root, case_name, report_text):
    """Fail closed on missing/mismatched evidence; termination is never success criteria."""
    case = CASES[case_name]
    finish = next((e["data"] for e in reversed(export["events"])
                   if e["kind"] == "finish"), {})
    assessment = {"assessment_version": 2, "case": case_name, "task_success": False,
                  "stop_reason": finish.get("status"),
                  "termination_source": finish.get("termination_source"),
                  "criteria": {}, "failures": [], "measurements": None}
    checks = assessment["criteria"]
    try:
        store = QuantumStore(root)
        events = export["events"]
        pairs = paired_execution(events)
        results = [e["data"] for e in events if e["kind"] == "tool_result"]
        checks["native_calls"] = True
        checks["no_tool_errors"] = not any(e["kind"] == "tool_error" for e in events)
        reports = [r["result"] for r in results if r["tool"] == "quantum_read_report"]
        checks["one_read_report"] = len(reports) == 1
        if not reports:
            raise ValueError("missing quantum_read_report evidence")
        report = reports[-1]
        saved = store.get(report["artifact_id"], "quantum_simulation")
        checks["saved_report_matches"] = {k: v for k, v in report.items()
                                           if k != "rendered"} == saved
        built = store.get(saved["circuit_id"], "quantum_circuit")
        spec = BuildCircuit.model_validate(built["spec"])
        checks["target"] = spec.target == case["target"] and spec.qubits == case["qubits"]
        checks["report_target"] = saved["target"] == case["target"]
        checks["parameters"] = saved["config"] == {
            "circuit_id": built["artifact_id"], "mode": case["mode"],
            "noise": case["noise"], "shots": 1024, "seed": 7}
        chain = [(r["tool"], r["result"]) for r in results]
        build_index = next(i for i, (t, r) in enumerate(chain)
                           if t == "build_circuit" and r == built)
        verify_index = next(i for i, (t, r) in enumerate(chain)
                            if t == "verify" and r.get("circuit_id") == built["artifact_id"]
                            and r.get("status") == "verified")
        sim_index = next(i for i, (t, r) in enumerate(chain)
                         if t == "run_simulation" and r == saved)
        read_index = next(i for i, (t, r) in enumerate(chain)
                          if t == "quantum_read_report" and r == report)
        checks["bound_ordered_chain"] = build_index < verify_index < sim_index < read_index
        # These two A2 cases require one unambiguous four-tool chain. Reject
        # duplicates/extra results instead of selecting a convenient matching row.
        checks["unique_case_chain"] = [p[1] for p in pairs] == [
            "build_circuit", "verify", "run_simulation", "quantum_read_report"]
        if not checks["unique_case_chain"]:
            raise ValueError("expected one build/verify/simulation/read chain")
        build_args, verify_args, sim_args, read_args = [p[2] for p in pairs]
        checks["build_request_binding"] = build_args == spec.model_dump()
        checks["verify_request_binding"] = (
            verify_args["circuit_id"] == built["artifact_id"] == pairs[1][3]["circuit_id"]
            and {k: v for k, v in pairs[1][3].items() if k != "circuit_id"}
            == built["verification"])
        checks["simulation_request_binding"] = (
            sim_args == QUANTUM_TOOLS["run_simulation"][0].model_validate(
                saved["config"]).model_dump() and sim_args["circuit_id"] == built["artifact_id"])
        checks["read_request_binding"] = read_args["result_id"] == saved["artifact_id"]
        ideal = independent_density(spec, CASES["bell_ideal"]["noise"])
        expected = independent_density(spec, case["noise"])
        target = np.zeros(2**spec.qubits)
        target[0] = target[-1] = 1/np.sqrt(2)
        ideal_fidelity = float(np.real(target @ ideal @ target))
        expected_fidelity = float(np.real(target @ expected @ target))
        observed = (np.array(saved["density_matrix"]["real"]) +
                    1j*np.array(saved["density_matrix"]["imag"]))
        measured = float(np.real(target @ observed @ target))
        checks["ideal_target_verified"] = bool(abs(ideal_fidelity-1) < 1e-10 and
            saved["verification"]["status"] == built["verification"]["status"] == "verified" and
            abs(saved["verification"]["ideal_premeasurement_fidelity"]-ideal_fidelity) < 1e-10)
        checks["independent_density"] = bool(np.allclose(observed, expected, atol=1e-10, rtol=0))
        checks["fidelity"] = bool(abs(measured-expected_fidelity) < 1e-10 and
                                  abs(measured-saved["premeasurement_fidelity"]) < 1e-10)
        counts = saved["counts"]
        checks["counts"] = bool(counts) and sum(counts.values()) == 1024 and all(
            len(k) == spec.qubits and set(k) <= {"0", "1"} and type(v) is int and v >= 0
            for k, v in counts.items())
        rendered = render_quantum_report(saved)
        checks["grounded_report"] = bool(report_text.strip()) and rendered in report_text and (
            report.get("rendered") == rendered)
        assessment["measurements"] = {
            "circuit_id": built["artifact_id"], "result_id": saved["artifact_id"],
            "ideal_target_fidelity": ideal_fidelity, "expected_fidelity": expected_fidelity,
            "reported_fidelity": saved["premeasurement_fidelity"],
            "density_matrix_fidelity": measured, "counts": counts,
            "expected_probabilities": {format(i, f"0{spec.qubits}b"): float(p)
                                       for i, p in enumerate(expected.diagonal().real)},
            "config": saved["config"], "versions": saved["versions"],
            "independent_method": "NumPy density evolution; Qiskit gate matrices; Pauli twirl (no Aer)",
            "caveat": "Ideal target verification is build correctness; noisy fidelity is a separate metric. Counts have sampling uncertainty."}
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        assessment["failures"].append(type(exc).__name__ + ": " + str(exc))
    assessment["failures"].extend(k for k, v in checks.items() if not v)
    assessment["task_success"] = bool(checks) and not assessment["failures"]
    return assessment
