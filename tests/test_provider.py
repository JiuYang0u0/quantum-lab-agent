import asyncio
import json
import time

import httpx
import pytest

from quantum_lab_agent.provider import Provider, Settings
from quantum_lab_agent.runtime import Agent, Trace


def test_nvidia_requires_explicit_model(monkeypatch):
    monkeypatch.delenv("QLA_MODEL", raising=False)
    with pytest.raises(ValueError):
        Settings.load("nvidia")


def test_roundtrip_protocol_and_key_not_in_trace(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith("models"):
            return httpx.Response(200, json={"data": [{"id": "test"}]})
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]})
    async def scenario():
        settings = Settings(base_url="http://localhost/v1", model="test", api_key="secret-value")
        trace = Trace(tmp_path / "t.db", [settings.api_key])
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = Provider(client, settings)
            assert "test" in await provider.models()
            result = await provider.complete([], [], time.monotonic() + 2)
            trace.event(trace.start("test"), "model", result)
        assert requests[1].headers["authorization"] == "Bearer secret-value"
        assert json.loads(requests[1].content)["max_tokens"] == 512
        assert "secret-value" not in (tmp_path / "t.db").read_bytes().decode(errors="ignore")
    asyncio.run(scenario())


def test_metadata_retained_without_reasoning():
    async def scenario():
        payload = {"choices": [{"finish_reason": "stop", "message": {
            "role": "assistant", "content": "OK", "reasoning_content": "PRIVATE REASONING"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 88, "total_tokens": 100,
                      "completion_tokens_details": {"reasoning_tokens": 82},
                      "reasoning_content": "PRIVATE REASONING"}}
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=payload))) as client:
            provider = Provider(client, Settings())
            message = await provider.complete([], [], time.monotonic() + 2)
        assert message == {"role": "assistant", "content": "OK"}
        assert provider.last_metadata["finish_reason"] == "stop"
        assert provider.last_metadata["usage"]["completion_tokens_details"]["reasoning_tokens"] == 82
        assert "PRIVATE REASONING" not in json.dumps([message, provider.last_metadata])
    asyncio.run(scenario())


@pytest.mark.parametrize("payload", [
    {"choices": []}, {"choices": [{"message": "not-object"}]},
    {"choices": [{"message": {"role": "assistant", "tool_calls": "bad"}}]},
    {"choices": [{"message": {"role": "assistant", "tool_calls": [{}]}}]},
])
def test_invalid_envelope_finishes_run(tmp_path, payload):
    async def scenario():
        trace = Trace(tmp_path / "trace.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=payload))) as client:
            outcome = await Agent(Provider(client, Settings()), client, "http://unused", trace).run("x")
        assert outcome["status"] == "provider_error"
        assert trace.export(outcome["run_id"])["events"][-1]["kind"] == "finish"
    asyncio.run(scenario())
