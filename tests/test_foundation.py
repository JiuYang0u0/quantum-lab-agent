import asyncio
import json

import httpx
import pytest

from quantum_lab_agent import runtime


def test_malformed_args_rejected():
    with pytest.raises(ValueError):
        runtime.validate_tool("qec_sample", {"sampling": {"test_shots": "10"}})
    with pytest.raises(ValueError):
        runtime.validate_tool("qec_read_report", {"result_id": "../secret"})
    with pytest.raises(ValueError):
        runtime.validate_tool("exec", {})


def test_redaction_and_replay(tmp_path):
    trace = runtime.Trace(tmp_path / "trace.db", secrets=["my-secret"])
    run = trace.start("use my-secret")
    trace.event(run, "tool_result", {"api_key": "abc", "text": "my-secret"})
    exported = trace.export(run)
    assert "my-secret" not in json.dumps(exported)
    assert "abc" not in json.dumps(exported)
    assert runtime.replay(exported) == runtime.replay(json.loads(json.dumps(exported)))


def test_uncertain_post_never_retried(tmp_path):
    calls = []
    def handler(request):
        calls.append(request.method)
        raise httpx.ReadTimeout("uncertain")
    async def scenario():
        trace = runtime.Trace(tmp_path / "trace.db")
        run = trace.start("test")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = runtime.QECAdapter(client, "http://qec", trace, run)
            for _ in range(2):
                with pytest.raises(runtime.ToolError):
                    await adapter.execute("qec_sample", {}, runtime.time.monotonic() + 1)
    asyncio.run(scenario())
    assert calls == ["POST"]


def test_job_polling_and_artifacts(tmp_path):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.method == "POST":
            return httpx.Response(202, json={"id": "job-a", "status": "queued"})
        if request.url.path == "/api/jobs/job-a":
            return httpx.Response(200, json={"id": "job-a", "status": "succeeded", "artifact_id": "dataset-a"})
        return httpx.Response(200, json={"datasets": [{"artifact_id": "dataset-a"}]})
    async def scenario():
        trace = runtime.Trace(tmp_path / "trace.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = runtime.QECAdapter(client, "http://qec", trace, trace.start("test"), poll_interval=0)
            result = await adapter.execute("qec_sample", {}, runtime.time.monotonic() + 2)
            assert result["artifact_id"] == "dataset-a"
            assert await adapter.execute("qec_list_artifacts", {}, runtime.time.monotonic() + 2)
    asyncio.run(scenario())
    assert calls == ["/api/jobs/sample", "/api/jobs/job-a", "/api/artifacts"]


def test_report_grounding():
    report = {"artifact_id": "comparison-a", "dataset_id": "dataset-a", "results": [{
        "decoder": "mwpm", "prediction_key": "prediction_0", "shots": 20, "errors": 2,
        "logical_error_rate": 0.1, "ci": [0.02, 0.3], "decode_seconds": 0.123,
    }]}
    rendered = runtime.render_report(report)
    assert "2/20" in rendered
    assert "0.1" in rendered
    assert "[comparison-a#prediction_0]" in rendered
    report["results"][0]["logical_error_rate"] = 0.9
    with pytest.raises(ValueError):
        runtime.render_report(report)


class FakeModel:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.calls = 0

    async def complete(self, messages, tools, deadline):
        self.calls += 1
        return next(self.messages)


def tool_message(name="qec_list_artifacts", arguments="{}"):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": "call-a", "type": "function", "function": {"name": name, "arguments": arguments}}
    ]}


def test_tool_budget_and_no_model_claims(tmp_path):
    async def scenario():
        trace = runtime.Trace(tmp_path / "trace.db")
        model = FakeModel([tool_message(), tool_message()])
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"datasets": []}))) as client:
            agent = runtime.Agent(model, client, "http://qec", trace, runtime.Limits(max_tools=1))
            result = await agent.run("list")
            assert result["status"] == "tool_budget"
            assert len([e for e in trace.export(result["run_id"])["events"] if e["kind"] == "tool_result"]) == 1
            model = FakeModel([{"role": "assistant", "content": "LER is 0.999"}])
            result = await runtime.Agent(model, client, "http://qec", trace).run("numbers")
            assert "0.999" not in result["output"]
    asyncio.run(scenario())
