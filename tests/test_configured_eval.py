import argparse
import asyncio
import importlib
import json
from pathlib import Path

import httpx
import pytest


@pytest.fixture
def script(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    module = importlib.import_module("configured_eval")
    monkeypatch.setattr(module, "load_dotenv", lambda *a, **kw: None)
    monkeypatch.setenv("QLA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("QLA_MODEL", "configured-exact-model")
    monkeypatch.setenv("QLA_API_KEY", "test-sensitive-value")
    monkeypatch.setenv("QLA_MAX_TOKENS", "2048")
    return module


def test_exact_settings_and_secret_exclusion(script):
    settings = script.configured_settings()
    assert settings.model == "configured-exact-model"
    assert settings.max_tokens == 2048
    assert settings.qec_url == "http://127.0.0.1:18000"
    assert "test-sensitive-value" not in json.dumps(settings.model_dump())


@pytest.mark.parametrize("status", [401, 403, 404, 429])
def test_provider_block_stops_without_retry_or_task(script, monkeypatch, tmp_path, status):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(script.httpx, "AsyncClient", lambda **kw: client)

    async def forbidden(*args, **kwargs):
        pytest.fail("task must not run after a blocked probe")

    monkeypatch.setattr(script, "multistep", forbidden)
    output = tmp_path / "evidence"
    assert asyncio.run(script.main(argparse.Namespace(output=str(output)))) == 1
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["model"] == "configured-exact-model"
    assert payload["max_tokens"] == 2048
    summary = json.loads((output / "probe-summary.json").read_text())
    assert summary["completion_attempt_log"][0]["http_status"] == status
    assert "test-sensitive-value" not in (output / "probe.json").read_text()


def test_native_roundtrip_preserves_id_and_passes_settings(script, monkeypatch, tmp_path):
    completions = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=[])
        payload = json.loads(request.content)
        completions.append(payload)
        message = {"role": "assistant", "content": "Received."}
        if len(completions) == 1:
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": "native-provider-call", "type": "function", "function": {
                    "name": "qec_list_artifacts", "arguments": "{}"}}]}
        return httpx.Response(200, json={"choices": [{"message": message,
                                                    "finish_reason": "stop"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(script.httpx, "AsyncClient", lambda **kw: client)
    received = []

    async def task(args, settings):
        received.append((args, settings))
        return 0

    monkeypatch.setattr(script, "multistep", task)
    assert asyncio.run(script.main(argparse.Namespace(output=str(tmp_path / "run")))) == 0
    assert len(completions) == 2
    assert completions[1]["messages"][-1]["tool_call_id"] == "native-provider-call"
    assert received[0][1].model == "configured-exact-model"
    assert received[0][1].max_tokens == 2048
