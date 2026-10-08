"""One native Gemma run, <=6 completions, no scripted tool calls or retry/fallback."""
import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx

from quantum_lab_agent.evaluation import assess
from quantum_lab_agent.provider import Provider, Settings
from quantum_lab_agent.runtime import Agent, Finalization, Limits, Trace

PROMPT = (
    "Run a tiny QEC experiment: sample a repetition code distance 3, rounds 1, p 0.03, "
    "seed 42 with train_shots 64, validation_shots 16, test_shots 32. "
    "Train an mlp for 1 epoch on the returned dataset using remaining CPU defaults. "
    "Compare that same dataset using the returned checkpoint against MWPM and lookup. "
    "Use only artifact IDs returned by your tools. Produce a grounded report with errors/shots, "
    "LER, CI, decode seconds and artifact citations, then stop. "
    "The compare tool already returns the report; no need to list artifacts."
)


class MeasuredProvider(Provider):
    async def complete(self, messages, tools, deadline):
        self.attempts += 1
        started = time.monotonic()
        try:
            return await super().complete(messages, tools, deadline)
        finally:
            self.last_metadata.setdefault("finish_reason", None)
            self.last_metadata.setdefault("usage", {})
            self.last_metadata.update(step=self.attempts, elapsed_seconds=time.monotonic() - started)
            self.attempt_log.append(dict(self.last_metadata))


async def main(args, settings=None):
    # Unique directory and exclusive file creation preserve all prior failures.
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    settings = settings or Settings(base_url="http://127.0.0.1:1234/v1", model="google/gemma-4-e2b",
                        api_key=Settings.load().api_key, qec_url="http://127.0.0.1:18000",
                        max_tokens=args.max_tokens)
    trace = Trace(output / "trace.sqlite3", [settings.api_key])
    started = time.monotonic()
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = MeasuredProvider(client, settings)
        provider.attempts, provider.attempt_log = 0, []
        outcome = await Agent(provider, client, settings.qec_url, trace,
                              Limits(max_steps=args.max_steps, max_tools=4, seconds=args.seconds),
                              finalization=Finalization(reports=1 if args.finalize_on_report else 0)).run(PROMPT)
    exported = trace.export(outcome["run_id"])
    summary = assess(exported)
    summary.update(elapsed_seconds=time.monotonic() - started,
                   completion_attempts=provider.attempts, completion_attempt_log=provider.attempt_log,
                   settings=settings.model_dump())
    for name, data in (("trace.json", exported), ("summary.json", summary)):
        (output / name).write_text(json.dumps(trace.clean(data), indent=2), encoding="utf-8")
    (output / "report.txt").write_text(outcome["output"], encoding="utf-8")
    trace.db.close()
    print(json.dumps(trace.clean(summary), indent=2))
    return 0 if summary["task_success"] and outcome["status"] in ("completed", "report_ready") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=6)
    parser.add_argument("--seconds", type=int, choices=range(180, 901), default=300)
    parser.add_argument("--finalize-on-report", action="store_true")
    raise SystemExit(asyncio.run(main(parser.parse_args())))
