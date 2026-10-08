"""Explicitly approved A2 NVIDIA run: two cases, <=10 completions, no retries."""
import argparse
import asyncio
import hashlib
import json
import subprocess
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values
from multistep_eval import MeasuredProvider

from quantum_lab_agent.provider import Settings
from quantum_lab_agent.quantum_evaluation import CASES, assess_quantum
from quantum_lab_agent.runtime import Agent, Limits, Trace

ROOT = Path(__file__).resolve().parents[1]


def settings_from_file():
    env = dotenv_values(ROOT / ".env")
    settings = Settings(base_url=env["QLA_BASE_URL"], model=env["QLA_MODEL"],
                        api_key=env["QLA_API_KEY"], max_tokens=int(env["QLA_MAX_TOKENS"]))
    if settings.base_url.rstrip("/") != "https://integrate.api.nvidia.com/v1":
        raise ValueError("A2 approval is NVIDIA-only")
    if settings.max_tokens != 2048:
        raise ValueError("A2 approval requires configured max_tokens=2048")
    return settings


async def main(output):
    settings = settings_from_file()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    revision = (await asyncio.to_thread(subprocess.check_output,
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)).strip()
    summaries = []
    async with httpx.AsyncClient(trust_env=False, transport=httpx.AsyncHTTPTransport(retries=0)) as client:
        for name, case in CASES.items():
            folder = output / name
            folder.mkdir()
            trace = Trace(folder / "trace.sqlite3", [settings.api_key])
            provider = MeasuredProvider(client, settings)
            provider.attempts, provider.attempt_log = 0, []
            prompt = (
                f"Build a correct {case['target']} target with {case['qubits']} qubits using "
                "build_circuit (H on q0 then CX from q0 to each other qubit, or matching preset). "
                "Call verify on its returned circuit_id for independent ideal target verification. "
                f"Then run_simulation mode={case['mode']}, noise={json.dumps(case['noise'])}, "
                "shots=1024, seed=7. Then quantum_read_report on the returned result artifact_id. "
                "Finally stop with a grounded report. Acknowledge ideal build verification is distinct "
                "from noisy premeasurement fidelity, which is not inferred from counts. "
                "Only use IDs returned by tools. Local Qiskit/Aer only. No plots or extra tasks. "
                "You have at most five completions, six tools, and 300 seconds."
            )
            started = time.monotonic()
            outcome = await Agent(provider, client, settings.qec_url, trace,
                                  Limits(max_steps=5, max_tools=6, seconds=300), family="quantum",
                                  quantum_root=folder / "artifacts").run(prompt)
            elapsed = time.monotonic() - started
            exported = trace.export(outcome["run_id"])
            summary = assess_quantum(exported, folder / "artifacts", name, outcome["output"])
            summary.update(completion_attempts=provider.attempts,
                           completion_attempt_log=provider.attempt_log,
                           elapsed_seconds=elapsed, tools_used=outcome["tools_used"],
                           settings=settings.model_dump(), source_revision=revision,
                           limits={"completions": 5, "tools": 6, "seconds": 300,
                                   "retries": 0, "interpretation_requests": 0})
            for filename, data in (("trace.json", exported), ("summary.json", summary)):
                (folder / filename).write_text(json.dumps(trace.clean(data), indent=2), encoding="utf-8")
            (folder / "report.txt").write_text(trace.clean(outcome["output"]), encoding="utf-8")
            summaries.append(trace.clean(summary))
            trace.db.close()
    aggregate = {"cases": summaries, "completion_attempts": sum(
        s["completion_attempts"] for s in summaries), "max_completions": 10,
        "task_success": all(s["task_success"] for s in summaries)}
    (output / "summary.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    hashes = {str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(json.dumps(aggregate, indent=2))
    return 0 if aggregate["task_success"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    raise SystemExit(asyncio.run(main(parser.parse_args().output)))
