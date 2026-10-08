import asyncio
import json
from pathlib import Path

import httpx
import pytest

from quantum_lab_agent.evaluation import assess
from quantum_lab_agent.runtime import Agent, Limits, Trace, replay
from quantum_lab_agent.schemas import tool_schemas

FIXTURE = json.loads((Path(__file__).parent / "fixtures/multistep.json").read_text())


def test_native_schemas_expose_nested_fields_without_refs():
    schemas = tool_schemas()
    assert '"$ref"' not in json.dumps(schemas)
    sample = next(s["function"]["parameters"] for s in schemas if s["function"]["name"] == "qec_sample")
    assert sample["properties"]["sampling"]["type"] == "object"
    assert sample["properties"]["sampling"]["properties"]["train_shots"]["type"] == "integer"


@pytest.mark.parametrize("fault", [None, "malformed", "nested_strings", "wrong_id", "missing_artifact", "step_budget", "report_wrong_id", "report_missing_mlp"])
def test_native_multistep(tmp_path, fault):
    posts = []

    def handler(request):
        if request.method == "POST":
            action = request.url.path.split("/")[-1]
            body = json.loads(request.content)
            posts.append((action, body))
            if action == "train" and body["dataset_id"] != "dataset-fixture":
                return httpx.Response(404)
            return httpx.Response(202, json={"id": "job-" + action})
        if "/api/jobs/" in request.url.path:
            action = request.url.path.split("job-")[-1]
            artifact = {"sample": "dataset", "train": "checkpoint", "compare": "comparison"}[action]
            job = {"id": "job-" + action, "status": "succeeded", "artifact_id": artifact + "-fixture"}
            if fault == "missing_artifact":
                del job["artifact_id"]
            return httpx.Response(200, json=job)
        report = json.loads(json.dumps(FIXTURE["report"]))
        if fault == "report_wrong_id":
            report["dataset_id"] = "dataset-unrelated"
        if fault == "report_missing_mlp":
            report["results"].pop()
        return httpx.Response(200, json=report)

    class Model:
        calls = 0

        async def complete(self, messages, tools, deadline):
            self.calls += 1
            if self.calls == 1:
                name, args = "qec_sample", FIXTURE["sample"]
                if fault == "nested_strings":
                    args = {"circuit": "repetition", "sampling": "train_shots=64"}
            else:
                previous = json.loads(messages[-1]["content"])
                if "error" in previous or self.calls == 4:
                    return {"role": "assistant", "content": "Finished; fake LER 0.999."}
                if self.calls == 2:
                    name, args = "qec_train", {"dataset_id": previous["artifact_id"]}
                    if fault == "wrong_id":
                        args["dataset_id"] = "dataset-invented"
                else:
                    dataset = json.loads(messages[3]["content"])["artifact_id"]
                    name, args = "qec_compare", {"dataset_id": dataset, "checkpoint_ids": [previous["artifact_id"]]}
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": f"call-{self.calls}", "type": "function", "function": {
                    "name": name, "arguments": "{" if fault == "malformed" else json.dumps(args)}}]}

    async def run():
        trace = Trace(tmp_path / "trace.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            outcome = await Agent(Model(), client, "http://qec", trace, Limits(
                max_steps=3 if fault == "step_budget" else 6, max_tools=4)).run("fixture")
        result = assess(trace.export(outcome["run_id"]))
        assert result["task_success"] is (fault in (None, "step_budget"))
        assert result["report_produced"] is (fault in (None, "step_budget"))
        assert result["termination_status"] == ("step_budget" if fault == "step_budget" else
                                               "completed" if fault is None else "completed_with_errors")
        assert "0.999" not in outcome["output"]
        if fault in (None, "step_budget"):
            assert posts[1][1]["dataset_id"] == "dataset-fixture"
            assert posts[2][1]["checkpoint_ids"] == ["checkpoint-fixture"]
            assert result["numeric_provenance"][2]["errors"] == 2
        if fault in ("malformed", "nested_strings"):
            assert not posts

    asyncio.run(run())


def assessment_trace(actions, training=None):
    """Synthetic successful tools; the evaluator must independently check lineage."""
    events = []
    for action, dataset, checkpoint in actions:
        name = "qec_" + action
        if action == "sample":
            args, result = FIXTURE["sample"], {"artifact_id": dataset}
        elif action == "train":
            args = {"dataset_id": dataset, "training": training or {}}
            result = {"artifact_id": checkpoint}
        else:
            args = {"dataset_id": dataset, "checkpoint_ids": [checkpoint]}
            result = json.loads(json.dumps(FIXTURE["report"]))
            result["dataset_id"] = dataset
            result["results"][2]["checkpoint_id"] = checkpoint
        events.extend([
            {"kind": "tool_call", "data": {"tool": name, "args": args}},
            {"kind": "tool_result", "data": {"tool": name, "result": result}},
        ])
    events.append({"kind": "finish", "data": {"status": "completed"}})
    return {"run_id": "synthetic-lineage", "events": events}


@pytest.mark.parametrize("actions,success", [
    # The reviewer's four-tool cross-dataset checkpoint reuse.
    ([("sample", "A", None), ("train", "A", "cpA"), ("sample", "B", None),
      ("compare", "B", "cpA")], False),
    ([("sample", "A", None), ("sample", "B", None), ("train", "A", "cpA"),
      ("compare", "B", "cpA")], False),
    ([("sample", "A", None), ("train", "A", "cpA"), ("sample", "B", None),
      ("train", "B", "cpB"), ("compare", "B", "cpA")], False),
    ([("sample", "A", None), ("train", "A", "cpA"), ("sample", "B", None),
      ("train", "B", "cpB"), ("compare", "B", "cpB")], True),
    # An earlier valid lineage remains usable after another dataset is sampled.
    ([("sample", "A", None), ("train", "A", "cpA"), ("sample", "B", None),
      ("compare", "A", "cpA")], True),
    ([("sample", "A", None), ("sample", "B", None), ("train", "A", "cpA"),
      ("compare", "A", "cpA")], True),
    ([("sample", "A", None), ("train", "A", "cpA"), ("compare", "A", "cpA"),
      ("sample", "B", None)], False),
])
def test_resampling_lineage(actions, success):
    result = assess(assessment_trace(actions))
    assert result["task_success"] is success
    if success:
        assert result["dataset_id"] == actions[-1][1]
        assert result["checkpoint_id"] == actions[-1][2]


@pytest.mark.parametrize("field,value", [
    ("architecture", "cnn"), ("epochs", 2), ("patience", 2), ("batch_size", 16),
    ("hidden_size", 16), ("learning_rate", 0.01), ("seed", 456),
    ("device", "cuda"), ("threads", 2),
])
def test_training_contract_overrides_fail(field, value):
    actions = [("sample", "A", None), ("train", "A", "cpA"), ("compare", "A", "cpA")]
    assert not assess(assessment_trace(actions, {field: value}))["task_success"]


def test_explicit_training_defaults_pass():
    actions = [("sample", "A", None), ("train", "A", "cpA"), ("compare", "A", "cpA")]
    defaults = {"architecture": "mlp", "epochs": 1, "patience": 1, "batch_size": 32,
                "hidden_size": 8, "learning_rate": 0.001, "seed": 123,
                "device": "cpu", "threads": 1}
    assert assess(assessment_trace(actions, defaults))["task_success"]


@pytest.mark.parametrize("attempt", [1, 2])
def test_historical_assessments_unchanged(attempt):
    root = Path(__file__).parents[1] / "docs/evidence"
    prefix = root / f"gemma-multistep-attempt-{attempt}"
    trace = json.loads(Path(str(prefix) + "-trace.json").read_text())
    expected = json.loads(Path(str(prefix) + "-assessment.json").read_text())
    assert assess(trace) == expected
    assert replay(trace) == Path(str(prefix) + "-report.txt").read_text()
