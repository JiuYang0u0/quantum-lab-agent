"""Configured NVIDIA probe (<=2 calls) then native multistep run (<=6 calls)."""
import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from multistep_eval import MeasuredProvider
from multistep_eval import main as multistep

from quantum_lab_agent.provider import Settings
from quantum_lab_agent.runtime import QECAdapter, Trace
from quantum_lab_agent.schemas import tool_schemas


def configured_settings():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    settings = Settings.load("nvidia")
    if settings.base_url.rstrip("/") != "https://integrate.api.nvidia.com/v1":
        raise ValueError("configured evaluation requires NVIDIA base URL")
    if settings.max_tokens != 2048:
        raise ValueError("configured evaluation requires the requested 2048-token budget")
    return settings.model_copy(update={"qec_url": "http://127.0.0.1:18000"})


class DiagnosticProvider(MeasuredProvider):
    async def complete(self, messages, tools, deadline):
        try:
            return await super().complete(messages, tools, deadline)
        except httpx.HTTPStatusError as exc:
            self.attempt_log[-1]["http_status"] = exc.response.status_code
            raise


async def main(args):
    settings = configured_settings()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    trace = Trace(output / "probe.sqlite3", [settings.api_key])
    run = trace.start("Native NVIDIA list-artifacts tool roundtrip; at most two completions")
    trace.event(run, "provider_settings", settings.model_dump())
    started = time.monotonic()
    deadline = started + 180
    status = "no_tool_calls"
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = DiagnosticProvider(client, settings)
        provider.attempts, provider.attempt_log = 0, []
        tools = [t for t in tool_schemas() if t["function"]["name"] == "qec_list_artifacts"]
        messages = [{"role": "user", "content":
                     "Call qec_list_artifacts once with empty arguments {}. "
                     "After receiving the result, acknowledge it briefly without calling more tools."}]
        try:
            first = await provider.complete(messages, tools, deadline)
            trace.event(run, "model", first)
            messages.append(first)
            calls = first.get("tool_calls") or []
            if len(calls) == 1 and calls[0]["function"]["name"] == "qec_list_artifacts":
                call = calls[0]
                arguments = json.loads(call["function"]["arguments"])
                trace.event(run, "tool_call", {"tool": "qec_list_artifacts", "args": arguments})
                result = await QECAdapter(client, settings.qec_url, trace, run).execute(
                    "qec_list_artifacts", arguments, deadline)
                trace.event(run, "tool_result", {"tool": "qec_list_artifacts", "result": result})
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result)})
                second = await provider.complete(messages, tools, deadline)
                trace.event(run, "model", second)
                status = "roundtrip_received" if not second.get("tool_calls") else "repeated_tool_call"
        except (TimeoutError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            status = type(exc).__name__
        summary = {"provider": "nvidia", "settings": settings.model_dump(), "status": status,
                   "elapsed_seconds": time.monotonic() - started,
                   "completion_attempts": provider.attempts,
                   "completion_attempt_log": provider.attempt_log}
        trace.event(run, "finish", summary)
    for name, data in (("probe.json", trace.export(run)), ("probe-summary.json", summary)):
        (output / name).write_text(json.dumps(trace.clean(data), indent=2), encoding="utf-8")
    print(json.dumps(trace.clean(summary), indent=2))
    trace.db.close()
    if status != "roundtrip_received":
        return 1
    args.output = str(output / "task")
    return await multistep(args, settings=settings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=6)
    parser.add_argument("--seconds", type=int, choices=range(180, 901), default=900)
    parser.set_defaults(finalize_on_report=True)
    raise SystemExit(asyncio.run(main(parser.parse_args())))
