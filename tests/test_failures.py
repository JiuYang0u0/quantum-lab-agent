import asyncio
import json

import httpx
import pytest
from test_foundation import FakeModel, tool_message

from quantum_lab_agent.runtime import Agent, Limits, QECAdapter, ToolError, Trace, time


@pytest.mark.parametrize("status", [404, 409, 422, 429, 500, 503])
def test_http_error_is_sanitized(tmp_path, status):
    async def scenario():
        trace = Trace(tmp_path / "t.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda r: httpx.Response(status, text="private-api-key"))) as client:
            with pytest.raises(ToolError, match=f"HTTP {status}") as exc:
                await QECAdapter(client, "http://qec", trace, trace.start("x")).execute(
                    "qec_list_artifacts", {}, time.monotonic() + 1)
            assert "private" not in str(exc.value)
    asyncio.run(scenario())


@pytest.mark.parametrize("state", ["failed", "alien", "running"])
def test_failed_or_stuck_job_bounded(tmp_path, state):
    async def scenario():
        trace = Trace(tmp_path / "t.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"id": "job-a", "status": state}))) as client:
            adapter = QECAdapter(client, "http://qec", trace, trace.start("x"), poll_interval=0.01)
            with pytest.raises((ToolError, TimeoutError)):
                await adapter.execute("qec_sample", {}, time.monotonic() + 0.04)
    asyncio.run(scenario())


def test_invalid_calls_consume_budget(tmp_path):
    async def scenario():
        trace = Trace(tmp_path / "t.db")
        model = FakeModel([tool_message(arguments="not-json"), tool_message()])
        async with httpx.AsyncClient() as client:
            outcome = await Agent(model, client, "http://unused", trace, Limits(max_tools=1)).run("x")
        assert outcome["status"] == "tool_budget"
        assert outcome["tools_used"] == 1
    asyncio.run(scenario())


def test_step_and_wall_limits(tmp_path):
    async def scenario():
        trace = Trace(tmp_path / "t.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))) as client:
            outcome = await Agent(FakeModel([tool_message()]), client, "http://qec", trace,
                                  Limits(max_steps=1)).run("x")
            assert outcome["status"] == "step_budget"
            class Slow:
                async def complete(self, *args):
                    await asyncio.sleep(1)
            outcome = await Agent(Slow(), client, "http://qec", trace, Limits(seconds=0.01)).run("x")
            assert outcome["status"] == "time_budget"
    asyncio.run(scenario())


def test_duplicate_completed_submission_reuses_job_after_reopen(tmp_path):
    posts = []
    def handler(request):
        if request.method == "POST":
            posts.append(1)
        return httpx.Response(200, json={"id": "job-a", "status": "succeeded", "artifact_id": "dataset-a"})
    async def scenario():
        path = tmp_path / "t.db"
        trace = Trace(path)
        run = trace.start("x")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            for _ in range(2):
                trace = Trace(path)
                await QECAdapter(client, "http://qec", trace, run).execute("qec_sample", {}, time.monotonic() + 1)
    asyncio.run(scenario())
    assert len(posts) == 1


def test_fake_model_actual_tool_roundtrip(tmp_path):
    class Model:
        calls = 0
        async def complete(self, messages, tools, deadline):
            self.calls += 1
            if self.calls == 1:
                return tool_message()
            assert messages[-1]["role"] == "tool"
            assert json.loads(messages[-1]["content"])["datasets"][0]["artifact_id"] == "dataset-test"
            return {"role": "assistant", "content": "invented 99%"}
    async def scenario():
        trace = Trace(tmp_path / "t.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"datasets": [{"artifact_id": "dataset-test"}]}))) as client:
            result = await Agent(Model(), client, "http://qec", trace).run("list")
            assert result["status"] == "completed"
            assert "99%" not in result["output"]
            assert "dataset-test" in result["output"]
    asyncio.run(scenario())


def test_all_failed_tools_not_success(tmp_path):
    async def scenario():
        trace = Trace(tmp_path / "t.db")
        model = FakeModel([tool_message(arguments="invalid"), {"role": "assistant", "content": "done"}])
        async with httpx.AsyncClient() as client:
            outcome = await Agent(model, client, "http://unused", trace).run("x")
        assert outcome["status"] == "completed_with_errors"
    asyncio.run(scenario())


def test_redaction_preserves_nonsecret_protocol_fields(tmp_path):
    trace = Trace(tmp_path / "t.db")
    assert trace.clean({"max_tokens": 256, "prediction_key": "prediction_0"}) == {
        "max_tokens": 256, "prediction_key": "prediction_0"}


def test_serialized_secrets_redacted(tmp_path):
    trace = Trace(tmp_path / "trace.db")
    secret = "EXAMPLE_PRIVATE_VALUE"
    inner = json.dumps({"api_key": secret})
    data = {"content": json.dumps({"nested": inner}), "tool_calls": [{
        "function": {"arguments": inner}}], "prose": f'Here is {{"api_key":"{secret}"}}'}
    run = trace.start("x")
    trace.event(run, "model", data)
    assert secret not in json.dumps(trace.export(run))
    assert secret.encode() not in (tmp_path / "trace.db").read_bytes()
