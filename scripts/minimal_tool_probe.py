"""List roundtrip then sample-only Agent: at most four real completions total."""
import asyncio
import json
from pathlib import Path

import httpx

from quantum_lab_agent.provider import Provider, Settings
from quantum_lab_agent.runtime import Agent, Limits, QECAdapter, Trace, time
from quantum_lab_agent.schemas import tool_schemas


async def main():
    settings = Settings.load().model_copy(update={"max_tokens": 512, "qec_url": "http://127.0.0.1:18000"})
    output = Path(".qla/live")
    trace = Trace(output / "live.sqlite3", [settings.api_key])
    run = trace.start("Minimal single-tool Gemma capability probe; at most two completions")
    trace.event(run, "provider_settings", settings.model_dump())
    messages = [{"role": "user", "content": "Call qec_list_artifacts now with empty arguments {}. Do not explain."}]
    tools = [t for t in tool_schemas() if t["function"]["name"] == "qec_list_artifacts"]
    status = "no_tool_calls"
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = Provider(client, settings)
        try:
            first = await provider.complete(messages, tools, time.monotonic() + 90)
            trace.event(run, "model", first)
            trace.event(run, "model_metadata", provider.last_metadata)
            messages.append(first)
            calls = first.get("tool_calls") or []
            if len(calls) == 1 and calls[0]["function"]["name"] == "qec_list_artifacts":
                call = calls[0]
                result = await QECAdapter(client, "http://127.0.0.1:18000", trace, run).execute(
                    "qec_list_artifacts", json.loads(call["function"]["arguments"]), time.monotonic() + 5)
                trace.event(run, "tool_result", {"tool": "qec_list_artifacts", "result": result})
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
                second = await provider.complete(messages, tools, time.monotonic() + 90)
                trace.event(run, "model", second)
                trace.event(run, "model_metadata", provider.last_metadata)
                status = "roundtrip_received" if not second.get("tool_calls") else "repeated_tool_call"
        except (TimeoutError, httpx.HTTPError, ValueError, KeyError) as exc:
            status = type(exc).__name__
        trace.event(run, "finish", {"status": status})
        if status == "roundtrip_received":
            outcome = await Agent(provider, client, "http://127.0.0.1:18000", trace,
                                  Limits(max_steps=2, max_tools=1, seconds=150)).run(
                "Call qec_sample exactly once with defaults (empty arguments {}). "
                "Do not list artifacts or call any other tool. After the dataset is created, stop.")
            (output / "lm-agent-sample-512.json").write_text(json.dumps(
                trace.export(outcome["run_id"]), indent=2), encoding="utf-8")
            print(json.dumps(outcome, indent=2))
    exported = trace.export(run)
    (output / "lm-minimal-probe-512.json").write_text(json.dumps(exported, indent=2), encoding="utf-8")
    print(json.dumps(exported, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
