import asyncio
import json
import time
from pathlib import Path

import httpx
import pytest

from quantum_lab_agent import runtime
from quantum_lab_agent.evaluation import assess
from quantum_lab_agent.provider import Provider, Settings

REPORT = json.loads((Path(__file__).parent / "fixtures/multistep.json").read_text())["report"]


def call(artifact):
    return {"role": "assistant", "content": None, "tool_calls": [{
        "id": artifact, "type": "function", "function": {
            "name": "qec_read_report", "arguments": json.dumps({"result_id": artifact})}}]}


def scenario(tmp_path, policy, reports, interpretation="stop", emitted=None):
    class Model:
        calls = 0

        def __init__(self):
            self.last_metadata = {}

        async def complete(self, messages, tools, deadline):
            self.calls += 1
            self.last_metadata = {"finish_reason": "tool_calls"}
            if self.calls <= len(reports):
                return call(reports[self.calls - 1]["artifact_id"])
            self.last_metadata = {"finish_reason": "stop"}
            return {"role": "assistant", "content": "done"}

        async def interpret(self, messages, deadline, max_tokens):
            self.calls += 1
            if emitted is not None:
                assert len(emitted) == 1
                assert runtime.render_report(REPORT) in emitted[0]["output"]
            assert 0 < deadline - time.monotonic() <= policy.interpretation_seconds + 1e-8
            assert max_tokens == policy.interpretation_tokens
            if interpretation == "timeout":
                await asyncio.sleep(1)
            self.last_metadata = {"finish_reason": "stop" if interpretation == "accepted" else interpretation}
            if interpretation == "accepted":
                return {"role": "assistant", "content": runtime.COMMENTARY[0]}
            return {"role": "assistant", "content": "LER is 0.999; secret=password"}

    async def run():
        model = Model()
        trace = runtime.Trace(tmp_path / "trace.db", ["password"])
        def handler(request):
            artifact = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, json=next(r for r in reports if r["artifact_id"] == artifact))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            outcome = await runtime.Agent(model, client, "http://qec", trace,
                                          finalization=policy,
                                          on_report=emitted.append if emitted is not None else None).run("declared report goal")
        return model, outcome, trace.export(outcome["run_id"])
    return asyncio.run(run())


def test_report_ready_stops_without_extra_completion(tmp_path):
    model, outcome, export = scenario(tmp_path, runtime.Finalization(reports=1), [REPORT])
    assert model.calls == 1
    assert outcome["status"] == "report_ready"
    assert outcome["task_completion"] == "verified_report_goal"
    assert runtime.render_report(REPORT) in outcome["output"]
    assessment = assess(export)
    assert assessment["termination_source"] == "policy"
    assert assessment["model_stop_observed"] is False


@pytest.mark.parametrize("fault", ["empty", "metrics"])
def test_invalid_report_cannot_finalize(tmp_path, fault):
    report = json.loads(json.dumps(REPORT))
    if fault == "empty":
        report["results"] = []
    else:
        report["results"][0]["logical_error_rate"] = 0.999
    model, outcome, _ = scenario(tmp_path, runtime.Finalization(reports=1), [report])
    assert model.calls == 2
    assert outcome["status"] == "completed_with_errors"
    assert outcome["task_completion"] == "unverified"


def test_multiple_distinct_reports_and_general_mode(tmp_path):
    second = {**REPORT, "artifact_id": "comparison-second"}
    model, outcome, _ = scenario(tmp_path, runtime.Finalization(reports=2), [REPORT, REPORT, second])
    assert model.calls == 3
    assert outcome["status"] == "report_ready"
    assert "comparison-second" in outcome["output"]
    model, outcome, _ = scenario(tmp_path, runtime.Finalization(), [REPORT, second])
    assert model.calls == 3
    assert outcome["status"] == "completed"


@pytest.mark.parametrize("reason,status", [("length", "truncated"), ("timeout", "time_budget"),
                                           ("stop", "rejected")])
def test_optional_interpretation_cannot_erase_or_pollute_report(tmp_path, reason, status):
    policy = runtime.Finalization(reports=1, interpret=True, interpretation_seconds=0.01)
    model, outcome, export = scenario(tmp_path, policy, [REPORT], reason)
    assert model.calls == 2
    assert outcome["status"] == "report_ready"
    assert outcome["interpretation_status"] == status
    assert runtime.render_report(REPORT) in outcome["output"]
    assert "0.999" not in outcome["output"]
    assert "password" not in json.dumps(export)
    assert export["events"][0]["data"]["finalization"]["interpretation_tokens"] == 128


def test_interpretation_has_dedicated_provider_budget():
    payloads = []
    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "role": "assistant", "content": "Smoke tests do not establish superiority."}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = Provider(client, Settings(max_tokens=1024))
            await provider.interpret([], time.monotonic() + 1, 64)
            assert provider.settings.max_tokens == 1024
    asyncio.run(run())
    assert payloads[0]["max_tokens"] == 64
    assert "tools" not in payloads[0]


def test_interpretation_requires_explicit_report_goal():
    with pytest.raises(ValueError):
        runtime.Finalization(interpret=True)


def test_report_emitted_before_accepted_commentary(tmp_path):
    emitted = []
    _, outcome, _ = scenario(tmp_path, runtime.Finalization(reports=1, interpret=True),
                             [REPORT], "accepted", emitted)
    assert outcome["interpretation_status"] == "completed"
    assert outcome["commentary"] == "Model commentary (conceptual): " + runtime.COMMENTARY[0]
    assert outcome["output"] == emitted[0]["output"]


def test_model_stop_before_report_goal_is_not_success(tmp_path):
    _, outcome, export = scenario(tmp_path, runtime.Finalization(reports=2), [REPORT])
    assert outcome["status"] == "report_goal_unmet"
    assert outcome["task_completion"] == "unverified"
    assert assess(export)["termination_source"] == "model"
    assert assess(export)["model_stop_observed"] is True


@pytest.mark.parametrize("kwargs", [{"reports": -1}, {"reports": 31},
                                   {"interpretation_seconds": 0}, {"interpretation_seconds": 61},
                                   {"interpretation_tokens": 15}, {"interpretation_tokens": 257}])
def test_finalization_budgets_validated(kwargs):
    with pytest.raises(ValueError):
        runtime.Finalization(**kwargs)


@pytest.mark.parametrize("fault", ["dataset", "checkpoint", "decoder"])
def test_report_goal_validates_comparison_contract(tmp_path, fault):
    report = json.loads(json.dumps(REPORT))
    if fault == "dataset":
        report["dataset_id"] = "unrelated"
    elif fault == "checkpoint":
        report["results"][2]["checkpoint_id"] = "unrelated"
    else:
        report["results"].pop()
    class Model:
        calls = 0
        async def complete(self, messages, tools, deadline):
            self.calls += 1
            if self.calls > 1:
                return {"role": "assistant", "content": "done"}
            message = call("comparison-fixture")
            message["tool_calls"][0]["function"] = {"name": "qec_compare", "arguments": json.dumps({
                "dataset_id": "dataset-fixture", "checkpoint_ids": ["checkpoint-fixture"]})}
            return message
    def handler(request):
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job-a"})
        if "/jobs/" in request.url.path:
            return httpx.Response(200, json={"id": "job-a", "status": "succeeded",
                                             "artifact_id": "comparison-fixture"})
        return httpx.Response(200, json=report)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            outcome = await runtime.Agent(Model(), client, "http://qec", runtime.Trace(tmp_path / "t.db"),
                                          finalization=runtime.Finalization(reports=1)).run("compare")
            assert outcome["status"] == "completed_with_errors"
    asyncio.run(run())


def test_original_900_trace_replayed_with_fewer_provider_calls(tmp_path, monkeypatch):
    original = json.loads((Path(__file__).parents[1] /
                           "docs/evidence/gemma-multistep-900-trace.json").read_text())
    expected = json.loads((Path(__file__).parents[1] /
                          "docs/evidence/gemma-multistep-900-assessment.json").read_text())
    assert assess(original) == expected
    messages = [e["data"] for e in original["events"] if e["kind"] == "model"]
    results = iter(e["data"] for e in original["events"] if e["kind"] == "tool_result")
    class Model:
        calls = 0
        async def complete(self, messages_arg, tools, deadline):
            self.calls += 1
            return messages[self.calls - 1]
    async def execute(self, name, arguments, deadline):
        recorded = next(results)
        assert name == recorded["tool"]
        return recorded["result"]
    monkeypatch.setattr(runtime.QECAdapter, "execute", execute)
    async def run():
        model = Model()
        outcome = await runtime.Agent(model, None, "http://offline", runtime.Trace(tmp_path / "t.db"),
                                      finalization=runtime.Finalization(reports=1)).run(original["prompt"])
        assert outcome["status"] == "report_ready"
        assert model.calls == 3
        assert len(messages) == 4
        assert outcome["output"] == runtime.replay(original)
    asyncio.run(run())


def test_policy_stops_remaining_calls_in_same_batch(tmp_path, monkeypatch):
    executed = []
    class Model:
        async def complete(self, messages, tools, deadline):
            message = call(REPORT["artifact_id"])
            message["tool_calls"].extend(call("unused-report")["tool_calls"])
            return message
    async def execute(self, name, arguments, deadline):
        executed.append(arguments)
        return REPORT
    monkeypatch.setattr(runtime.QECAdapter, "execute", execute)
    async def run():
        return await runtime.Agent(Model(), None, "http://offline", runtime.Trace(tmp_path / "t.db"),
                                   finalization=runtime.Finalization(reports=1)).run("single report")
    assert asyncio.run(run())["status"] == "report_ready"
    assert len(executed) == 1


def test_cli_report_emission_and_exit_code(tmp_path, monkeypatch, capsys):
    from quantum_lab_agent import cli
    async def complete(self, messages, tools, deadline):
        return call(REPORT["artifact_id"])
    async def execute(self, name, arguments, deadline):
        return REPORT
    async def interpret(self, messages, deadline, max_tokens):
        assert "report_ready" in capsys.readouterr().out
        raise TimeoutError
    monkeypatch.setattr(Provider, "complete", complete)
    monkeypatch.setattr(Provider, "interpret", interpret)
    monkeypatch.setattr(runtime.QECAdapter, "execute", execute)
    monkeypatch.setattr("sys.argv", ["qla", "--trace-db", str(tmp_path / "t.db"), "run",
                                     "--finalize-on-report", "--interpret", "--prompt", "report"])
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    assert exit_info.value.code == 0
    final = json.loads(capsys.readouterr().out)
    assert final["interpretation_status"] == "time_budget"
    assert "output" not in final
