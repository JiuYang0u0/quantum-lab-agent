import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

from .provider import Provider, Settings
from .runtime import Agent, Finalization, Limits, Trace, replay


async def execute(args):
    trace_path = Path(args.trace_db)
    if args.command == "replay":
        print(replay(json.loads(Path(args.file).read_text(encoding="utf-8"))))
        return 0
    if args.command == "export":
        data = Trace(trace_path).export(args.run_id)
        Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(args.output)
        return 0
    if args.command == "quantum-tool":
        import time

        from .quantum import QuantumAdapter
        result = await QuantumAdapter(args.artifact_root).execute(
            args.tool, json.loads(args.arguments), time.monotonic() + 120)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    settings = Settings.load(args.profile)
    trace = Trace(trace_path, [settings.api_key])
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
        provider = Provider(client, settings)
        if args.command == "doctor":
            result = {"settings": settings.model_dump(), "tool_capability": "unverified (use --probe-tools)"}
            try:
                models = await provider.models()
                result.update(models=models, model_present=settings.model in models)
            except (httpx.HTTPError, ValueError, KeyError):
                result["model_error"] = "models endpoint unavailable or invalid"
            try:
                health = await client.get(settings.qec_url + "/api/health", timeout=5)
                result["qec_health"] = {"http_status": health.status_code, "body": health.json()}
            except (httpx.HTTPError, ValueError):
                result["qec_health"] = {"error": "unavailable"}
            if args.probe_tools:
                outcome = await Agent(provider, client, settings.qec_url, trace,
                                      Limits(max_steps=2, max_tools=1, seconds=60)).run(
                    "Call qec_list_artifacts with {} exactly once. After receiving the tool result, stop.")
                events = trace.export(outcome["run_id"])["events"]
                success = any(e["kind"] == "tool_result" for e in events)
                result["tool_capability"] = "tool executed" if success else "probe failed"
                result["probe"] = outcome
            print(json.dumps(trace.clean(result), ensure_ascii=False, indent=2))
            return 0 if result.get("model_present") and (not args.probe_tools or success) else 1
        if args.report_count is not None and not args.finalize_on_report:
            raise ValueError("--report-count requires --finalize-on-report")
        policy = Finalization(reports=(args.report_count or 1) if args.finalize_on_report else 0,
                              interpret=args.interpret,
                              interpretation_tokens=args.interpretation_tokens,
                              interpretation_seconds=args.interpretation_seconds)
        def emit_report(data):
            print(json.dumps({"event": "report_ready", **data}, ensure_ascii=False), flush=True)
        outcome = await Agent(provider, client, settings.qec_url, trace,
                              Limits(max_steps=args.max_steps, max_tools=args.max_tools,
                                     seconds=args.seconds), finalization=policy,
                              on_report=emit_report if policy.interpret else None,
                              family=args.family, quantum_root=args.artifact_root).run(args.prompt)
        if policy.interpret and outcome["status"] == "report_ready":
            outcome.pop("output")  # Already flushed before optional commentary; never duplicate tables.
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0 if outcome["status"] in ("completed", "report_ready") else 1


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Bounded QEC lab agent (milestone 1)")
    parser.add_argument("--profile", choices=["lmstudio", "nvidia"], default=os.getenv("QLA_PROFILE", "lmstudio"))
    parser.add_argument("--trace-db", default=os.getenv("QLA_TRACE_DB", ".qla/trace.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--probe-tools", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--family", choices=["qec", "quantum"], default="qec")
    run.add_argument("--artifact-root", default=".qla/quantum")
    run.add_argument("--prompt", required=True)
    run.add_argument("--max-steps", type=int, default=6)
    run.add_argument("--max-tools", type=int, default=5)
    run.add_argument("--seconds", type=float, default=120)
    run.add_argument("--finalize-on-report", action="store_true",
                     help="Declare a report-only goal; stop after verified reports")
    run.add_argument("--report-count", type=int, choices=range(1, 31),
                     help="Distinct reports required (default 1); requires --finalize-on-report")
    run.add_argument("--interpret", action="store_true", help="Optional constrained conceptual caveat")
    run.add_argument("--interpretation-tokens", type=int, default=128)
    run.add_argument("--interpretation-seconds", type=float, default=15)
    export = sub.add_parser("export")
    export.add_argument("run_id")
    export.add_argument("--output", required=True)
    sub.add_parser("replay").add_argument("file")
    from .quantum_types import QUANTUM_TOOLS
    local = sub.add_parser("quantum-tool", help="Offline local quantum operation; no provider")
    local.add_argument("tool", choices=list(QUANTUM_TOOLS))
    local.add_argument("--arguments", required=True, help="Restricted JSON tool arguments")
    local.add_argument("--artifact-root", default=".qla/quantum")
    try:
        code = asyncio.run(execute(parser.parse_args()))
    except (ValueError, OSError):
        print("Configuration, file or trace error; check arguments and environment.", file=sys.stderr)
        code = 2
    raise SystemExit(code)
