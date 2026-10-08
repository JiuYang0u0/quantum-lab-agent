import asyncio
import copy
import hashlib
import json
import time
from pathlib import Path

import pytest

from quantum_lab_agent.quantum import QuantumAdapter
from quantum_lab_agent.quantum_evaluation import CASES, assess_quantum


def evidence(tmp_path, name="bell_ideal", overrides=None):
    case = copy.deepcopy(CASES[name])
    adapter = QuantumAdapter(tmp_path)
    events = []

    def call(tool, args):
        events.append({"kind": "model", "data": {"tool_calls": [
            {"id": str(len(events)), "function": {"name": tool, "arguments": json.dumps(args)}}]}})
        events.append({"kind": "tool_call", "data": {"tool": tool, "args": args}})
        result = asyncio.run(adapter.execute(tool, args, time.monotonic()+60))
        events.append({"kind": "tool_result", "data": {"tool": tool, "result": result}})
        return result

    built = call("build_circuit", {"target": case["target"], "preset": case["target"],
                                   "qubits": case["qubits"], **(overrides or {})})
    call("verify", {"circuit_id": built["artifact_id"]})
    simulated = call("run_simulation", {"circuit_id": built["artifact_id"],
                     "mode": case["mode"], "noise": case["noise"], "shots": 1024, "seed": 7})
    report = call("quantum_read_report", {"result_id": simulated["artifact_id"]})
    events.append({"kind": "finish", "data": {"status": "step_budget",
                                              "termination_source": "budget_or_error"}})
    return {"events": events}, report["rendered"]


@pytest.mark.parametrize("case", CASES)
def test_offline_acceptance_independent_of_termination(tmp_path, case):
    trace, report = evidence(tmp_path, case)
    result = assess_quantum(trace, tmp_path, case, report)
    assert result["task_success"], result
    assert result["stop_reason"] == "step_budget"


@pytest.mark.parametrize("mutation", ["empty", "wrong_target", "noise", "mismatch", "native"])
def test_reject_bad_evidence(tmp_path, mutation):
    overrides = {"preset": None, "gates": []} if mutation == "mismatch" else None
    trace, report = evidence(tmp_path, overrides=overrides)
    case = "bell_ideal"
    if mutation == "empty":
        report = ""
    elif mutation == "wrong_target":
        case = "ghz3_gate_noise"
    elif mutation == "noise":
        trace = copy.deepcopy(trace)
        trace["events"][-2]["data"]["result"]["config"]["noise"]["readout"] = 0.2
    elif mutation == "native":
        trace["events"][0]["data"]["tool_calls"][0]["function"]["arguments"] = "{}"
    assert not assess_quantum(trace, tmp_path, case, report)["task_success"]


def test_missing_report(tmp_path):
    assert not assess_quantum({"events": []}, tmp_path, "bell_ideal", "")["task_success"]


def replace_arguments(trace, tool, change):
    """Mutate both native and execution arguments, leaving all results intact."""
    for event in trace["events"]:
        if event["kind"] == "model":
            for call in event["data"].get("tool_calls", []):
                if call["function"]["name"] == tool:
                    args = json.loads(call["function"]["arguments"])
                    change(args)
                    call["function"]["arguments"] = json.dumps(args)
        elif event["kind"] == "tool_call" and event["data"]["tool"] == tool:
            change(event["data"]["args"])


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("attack", ["read_id", "verify_id", "simulation_id", "seed", "shots",
                                    "noise", "build_target", "build_gates"])
def test_requests_bound_to_results(tmp_path, case, attack):
    trace, report = evidence(tmp_path, case)
    tool, changes = {
        "read_id": ("quantum_read_report", {"result_id": "0" * 64}),
        "verify_id": ("verify", {"circuit_id": "0" * 64}),
        "simulation_id": ("run_simulation", {"circuit_id": "0" * 64}),
        "seed": ("run_simulation", {"seed": 999}),
        "shots": ("run_simulation", {"shots": 1}),
        "noise": ("run_simulation", {"mode": "noisy", "noise": {"depolarizing_1q": 0.9}}),
        "build_target": ("build_circuit", {"target": "ghz" if case == "bell_ideal" else "bell",
                                            "qubits": 2, "preset": "ghz" if case == "bell_ideal" else "bell"}),
        "build_gates": ("build_circuit", {"preset": None, "gates": []}),
    }[attack]
    replace_arguments(trace, tool, lambda args: args.update(changes))
    result = assess_quantum(trace, tmp_path, case, report)
    assert not result["task_success"], result
    assert result["criteria"]["native_calls"]


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("explicit_gates", [False, True])
def test_normalized_defaults_and_batched_native_calls(tmp_path, case, explicit_gates):
    overrides = None
    if explicit_gates:
        overrides = {"preset": None, "gates": [{"name": "h", "qubits": [0]}] + [
            {"name": "cx", "qubits": [0, q]} for q in range(1, CASES[case]["qubits"])]}
    trace, report = evidence(tmp_path, case, overrides)
    # Fully explicit schema defaults match the saved spec, including gate angles.
    from quantum_lab_agent.quantum_types import QUANTUM_TOOLS
    replace_arguments(trace, "build_circuit", lambda args: args.update(
        QUANTUM_TOOLS["build_circuit"][0].model_validate(args).model_dump()))
    # Omitted simulation defaults and zero readout are equivalent to explicit values.
    def omit_defaults(args):
        args.pop("shots")
        args.pop("seed")
        args["noise"].pop("readout")
        if case == "bell_ideal":
            args.pop("mode")
            args.pop("noise")
    replace_arguments(trace, "run_simulation", omit_defaults)
    # Real Bell trace batches verify + simulate; preserve their native queue order.
    trace["events"][3]["data"]["tool_calls"].extend(trace["events"][6]["data"]["tool_calls"])
    del trace["events"][6]
    result = assess_quantum(trace, tmp_path, case, report)
    assert result["assessment_version"] == 2
    assert result["task_success"], result


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("attack", ["duplicate_id", "duplicate_result", "reorder_results",
                                    "orphan_result", "wrong_result_name", "early_model"])
def test_ambiguous_execution_rejected(tmp_path, case, attack):
    trace, report = evidence(tmp_path, case)
    events = trace["events"]
    if attack == "duplicate_id":
        events[3]["data"]["tool_calls"][0]["id"] = events[0]["data"]["tool_calls"][0]["id"]
    elif attack == "duplicate_result":
        events.insert(3, copy.deepcopy(events[2]))
    elif attack == "reorder_results":
        events[2], events[5] = events[5], events[2]
    elif attack == "orphan_result":
        del events[1]
    elif attack == "wrong_result_name":
        events[2]["data"]["tool"] = "verify"
    elif attack == "early_model":
        events[2], events[3] = events[3], events[2]
    assert not assess_quantum(trace, tmp_path, case, report)["task_success"]


def test_archived_traces_and_hashes_unchanged():
    root = Path(__file__).resolve().parents[1] / "docs/evidence/a2-nvidia-20261008"
    for name, digest in json.loads((root / "manifest.json").read_text()).items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
    for case in CASES:
        folder = root / case
        result = assess_quantum(json.loads((folder / "trace.json").read_text(encoding="utf-8")),
                                folder / "artifacts", case,
                                (folder / "report.txt").read_text(encoding="utf-8"))
        assert result["assessment_version"] == 2
        assert result["task_success"], result
