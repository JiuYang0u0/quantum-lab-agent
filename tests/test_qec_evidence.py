"""Offline mutations of the actual A3 wrappers, including full verifier probes."""
import copy
import json
import runpy
from pathlib import Path

import pytest

from quantum_lab_agent.qec_evidence import assess_bound_qec
from quantum_lab_agent.schemas import validate_tool

ROOT = Path(__file__).resolve().parents[1] / "docs/evidence/a3-nvidia-web-20261009"


@pytest.fixture
def trace():
    return json.loads((ROOT / "qec-trace.json").read_text())


def native(trace, name):
    return next(c["function"] for e in trace["events"] if e["kind"] == "model"
                for c in e["data"].get("tool_calls", []) if c["function"]["name"] == name)


def jobs(trace, name):
    return [e["data"] for e in trace["events"] if e["kind"] == "job"
            and e["data"]["kind"] == name]


def change_request(args, name):
    if name == "sample":
        args["circuit"]["p"] = 0.04
    elif name == "train":
        args["dataset_id"] = "dataset-wrong"
    else:
        args["benchmark"] = {"repeats": 2}


@pytest.mark.parametrize("name", ["sample", "train", "compare"])
@pytest.mark.parametrize("layer", ["native", "executed", "job"])
def test_parameter_binding(trace, name, layer):
    if layer == "native":
        call = native(trace, "qec_" + name)
        args = json.loads(call["arguments"])
        change_request(args, name)
        call["arguments"] = json.dumps(args)
    elif layer == "executed":
        call = next(e["data"] for e in trace["events"] if e["kind"] == "tool_call"
                    and e["data"]["tool"] == "qec_" + name)
        change_request(call["args"], name)
    else:
        for job in jobs(trace, name):
            change_request(job["request"], name)
    assert not assess_bound_qec(trace)["task_success"]


@pytest.mark.parametrize("name", ["sample", "train", "compare"])
@pytest.mark.parametrize("field,value", [("artifact_id", "wrong"), ("id", "wrong"),
                                        ("status", "failed"), ("kind", "wrong")])
def test_terminal_job_binding(trace, name, field, value):
    jobs(trace, name)[-1][field] = value
    assert not assess_bound_qec(trace)["task_success"]


@pytest.mark.parametrize("name", ["sample", "train"])
@pytest.mark.parametrize("field,value", [("artifact_id", "wrong"), ("job_id", "wrong"),
                                        ("status", "failed")])
def test_result_wrapper(trace, name, field, value):
    result = next(e["data"]["result"] for e in trace["events"] if e["kind"] == "tool_result"
                  and e["data"]["tool"] == "qec_" + name)
    result[field] = value
    assert not assess_bound_qec(trace)["task_success"]


@pytest.mark.parametrize("mutation", ["duplicate_id", "orphan", "duplicate", "reorder", "missing"])
def test_serial_integrity(trace, mutation):
    events = trace["events"]
    models = [e for e in events if e["kind"] == "model"]
    calls = [i for i, e in enumerate(events) if e["kind"] == "tool_call"]
    if mutation == "duplicate_id":
        models[1]["data"]["tool_calls"][0]["id"] = models[0]["data"]["tool_calls"][0]["id"]
    elif mutation == "orphan":
        events.insert(0, copy.deepcopy(events[calls[0]]))
    elif mutation == "duplicate":
        events.insert(calls[0], copy.deepcopy(events[calls[0]]))
    elif mutation == "reorder":
        events[calls[0]], events[calls[1]] = events[calls[1]], events[calls[0]]
    else:
        del events[calls[0]]
    assert not assess_bound_qec(trace)["task_success"]


def test_normalized_defaults(trace):
    for name in ("qec_sample", "qec_train", "qec_compare"):
        call = native(trace, name)
        call["arguments"] = json.dumps(validate_tool(name, json.loads(call["arguments"])))
    assert assess_bound_qec(trace)["task_success"]


@pytest.mark.parametrize("field", ["artifact_id", "dataset_id", "checkpoint", "config", "benchmark"])
def test_comparison_result_lineage(trace, field):
    report = next(e["data"]["result"] for e in trace["events"] if e["kind"] == "tool_result"
                  and e["data"]["tool"] == "qec_compare")
    if field == "checkpoint":
        report["results"][-1]["checkpoint_id"] = "checkpoint-wrong"
    elif field == "config":
        report["config"]["p"] = 0.04
    elif field == "benchmark":
        report["benchmark"]["repeats"] = 2
    else:
        report[field] = "wrong"
    assert not assess_bound_qec(trace)["task_success"]


def test_service_noise_override_not_discarded(trace):
    for job in jobs(trace, "sample"):
        job["request"]["circuit"]["after_reset_flip_probability"] = 0.1
    assert not assess_bound_qec(trace)["task_success"]


@pytest.mark.parametrize("layer", ["native", "job"])
def test_full_verifier_rejects_original_probes(trace, monkeypatch, capsys, layer):
    if layer == "native":
        call = native(trace, "qec_train")
        args = json.loads(call["arguments"])
        args["dataset_id"] = "dataset-wrong"
        call["arguments"] = json.dumps(args)
    else:
        for job in jobs(trace, "train"):
            job["request"]["dataset_id"] = "dataset-wrong"
    read = Path.read_text

    def mutated_read(path, *args, **kwargs):
        return json.dumps(trace) if path == ROOT / "qec-trace.json" else read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mutated_read)
    with pytest.raises(AssertionError):
        runpy.run_path(str(ROOT / "verify.py"))
    assert "PASS:" not in capsys.readouterr().out


def test_full_verifier_accepts_archive(capsys):
    runpy.run_path(str(ROOT / "verify.py"))
    assert "PASS:" in capsys.readouterr().out
