"""Opt-in real HTTP CPU integration; optional LM probe uses at most two completions."""
import argparse
import asyncio
import json
from pathlib import Path

import httpx

from quantum_lab_agent.provider import Provider, Settings
from quantum_lab_agent.runtime import Agent, Limits, QECAdapter, Trace, replay, time


async def main(args):
    settings = Settings.load()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    trace = Trace(output / "live.sqlite3", [settings.api_key])
    async with httpx.AsyncClient(trust_env=False) as client:
        run = trace.start("deterministic CPU integration: sample -> train -> compare -> read -> list")
        adapter = QECAdapter(client, args.qec_url, trace, run)
        deadline = time.monotonic() + 120
        async def call(name, arguments):
            trace.event(run, "tool_call", {"tool": name, "args": arguments})
            result = await adapter.execute(name, arguments, deadline)
            trace.event(run, "tool_result", {"tool": name, "result": result})
            return result
        sample = await call("qec_sample", {"circuit": {"rounds": 1}, "sampling": {
            "train_shots": 64, "validation_shots": 16, "test_shots": 32}})
        trained = await call("qec_train", {"dataset_id": sample["artifact_id"]})
        report = await call("qec_compare", {"dataset_id": sample["artifact_id"],
                                            "checkpoint_ids": [trained["artifact_id"]]})
        await call("qec_read_report", {"result_id": report["artifact_id"]})
        await call("qec_list_artifacts", {})
        trace.event(run, "finish", {"status": "completed"})
        exported = trace.export(run)
        (output / "qec-integration.json").write_text(json.dumps(exported, indent=2), encoding="utf-8")
        (output / "report.txt").write_text(replay(exported), encoding="utf-8")
        summary = {"qec_run_id": run, "dataset_id": sample["artifact_id"],
                   "checkpoint_id": trained["artifact_id"], "comparison_id": report["artifact_id"]}
        if args.with_model:
            provider = Provider(client, settings)
            summary["models"] = await provider.models()
            outcome = await Agent(provider, client, args.qec_url, trace,
                                  Limits(max_steps=2, max_tools=1, seconds=90)).run(
                "Call qec_list_artifacts with {} exactly once. When its result arrives, stop.")
            summary["model_probe"] = outcome
            (output / "lm-tool-roundtrip.json").write_text(json.dumps(trace.export(outcome["run_id"]), indent=2), encoding="utf-8")
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qec-url", default="http://127.0.0.1:18000")
    parser.add_argument("--output", default=".qla/live")
    parser.add_argument("--with-model", action="store_true")
    asyncio.run(main(parser.parse_args()))
