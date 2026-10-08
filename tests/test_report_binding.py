import asyncio
import copy
import json
import time
from pathlib import Path

import httpx
import pytest

from quantum_lab_agent.runtime import (
    Agent,
    Finalization,
    QECAdapter,
    ToolError,
    Trace,
    verify_report_goal,
)

REPORT = json.loads((Path(__file__).parent / "fixtures/multistep.json").read_text())["report"]
ARGS = {"dataset_id": "dataset-fixture", "checkpoint_ids": ["checkpoint-fixture"]}


def handler(report):
    def respond(request):
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job-a"})
        if "/jobs/" in request.url.path:
            return httpx.Response(200, json={"id": "job-a", "status": "succeeded",
                                             "artifact_id": REPORT["artifact_id"]})
        return httpx.Response(200, json=report)
    return respond


def test_failed_compare_then_read_cannot_finalize(tmp_path):
    report = {**REPORT, "dataset_id": "unrelated"}

    class Model:
        calls = 0

        async def complete(self, messages, tools, deadline):
            self.calls += 1
            if self.calls == 3:
                return {"role": "assistant", "content": "done"}
            name, args = (("qec_compare", ARGS) if self.calls == 1 else
                          ("qec_read_report", {"result_id": REPORT["artifact_id"]}))
            return {"role": "assistant", "tool_calls": [{"id": str(self.calls),
                    "type": "function", "function": {"name": name,
                    "arguments": json.dumps(args)}}]}

    async def run():
        trace = Trace(tmp_path / "trace.db")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler(report))) as client:
            result = await Agent(Model(), client, "http://qec", trace,
                                 finalization=Finalization(reports=1)).run("compare then read")
        assert result["status"] == "completed_with_errors"
        assert result["task_completion"] == "unverified"
        events = trace.export(result["run_id"])["events"]
        assert len([e for e in events if e["kind"] == "tool_error"]) == 2
        assert not any(e["kind"] in ("tool_result", "report_ready") for e in events)
    asyncio.run(run())


@pytest.mark.parametrize("initial_fault", [None, "dataset", "fetch"])
def test_first_binding_survives_failed_validation_or_fetch_and_new_run(tmp_path, initial_fault):
    async def run():
        path = tmp_path / "trace.db"
        trace = Trace(path)
        report = {**REPORT, "dataset_id": "unrelated"} if initial_fault == "dataset" else REPORT
        fail_fetch = initial_fault == "fetch"

        def respond(request):
            if fail_fetch and "/results/" in request.url.path:
                return httpx.Response(503)
            return handler(report)(request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            deadline = time.monotonic() + 10
            adapter = QECAdapter(client, "http://qec", trace, trace.start("compare"))
            if initial_fault:
                with pytest.raises(ToolError):
                    await adapter.execute("qec_compare", ARGS, deadline)
            else:
                assert await adapter.execute("qec_compare", ARGS, deadline) == REPORT
            trace.db.close()
            trace = Trace(path)
            adapter = QECAdapter(client, "http://qec", trace, trace.start("read"))
            fail_fetch = False
            report = {**REPORT, "dataset_id": "unrelated"}
            with pytest.raises(ToolError):
                await adapter.execute("qec_read_report", {"result_id": REPORT["artifact_id"]}, deadline)
            # A report that actually satisfies the original requirements is still usable.
            report = REPORT
            assert await adapter.execute("qec_read_report", {
                "result_id": REPORT["artifact_id"]}, deadline) == REPORT
    asyncio.run(run())


@pytest.mark.parametrize("conflict", ["dataset", "checkpoints"])
def test_bindings_survive_reopen_new_run_and_conflicting_compare(tmp_path, conflict):
    async def run():
        path = tmp_path / "trace.db"
        trace = Trace(path)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler(REPORT))) as client:
            adapter = QECAdapter(client, "http://qec", trace, trace.start("first"))
            deadline = time.monotonic() + 10
            assert await adapter.execute("qec_compare", ARGS, deadline) == REPORT
            wrong = {**ARGS, "dataset_id": "unrelated"} if conflict == "dataset" else {
                **ARGS, "checkpoint_ids": ["other-checkpoint"]}
            with pytest.raises(ToolError):
                await adapter.execute("qec_compare", wrong, deadline)
            trace.db.close()
            trace = Trace(path)
            adapter = QECAdapter(client, "http://qec/", trace, trace.start("second"))
            with pytest.raises(ToolError):
                await adapter.execute("qec_read_report", {"result_id": REPORT["artifact_id"]}, deadline)
            with pytest.raises(ToolError):
                await adapter.execute("qec_compare", ARGS, deadline)
            # Existing, unbound reports on another service remain readable.
            other = QECAdapter(client, "http://other", trace, adapter.run_id)
            assert await other.execute("qec_read_report", {
                "result_id": REPORT["artifact_id"]}, deadline) == REPORT
    asyncio.run(run())


@pytest.mark.parametrize("fault", ["mwpm", "lookup", "duplicate", "unsupported", "missing"])
def test_checkpoint_association_rejected(fault):
    report = copy.deepcopy(REPORT)
    learned = report["results"][2]
    if fault in ("mwpm", "lookup"):
        baseline = next(r for r in report["results"] if r["decoder"] == fault)
        baseline["checkpoint_id"] = learned.pop("checkpoint_id")
        learned["decoder"] = "unrelated"
    elif fault == "duplicate":
        report["results"].append({**learned, "decoder": "cnn"})
    elif fault == "unsupported":
        learned["decoder"] = "transformer"
    else:
        learned.pop("checkpoint_id")
    with pytest.raises(ToolError):
        verify_report_goal("qec_compare", ARGS, report)


@pytest.mark.parametrize("decoders", [("mlp",), ("cnn",), ("mlp", "cnn"), ("mlp", "mlp")])
def test_supported_learned_decoders_have_one_checkpoint_each(decoders):
    report = copy.deepcopy(REPORT)
    learned = report["results"].pop()
    checkpoints = [f"checkpoint-{i}" for i in range(len(decoders))]
    report["results"].extend({**learned, "decoder": decoder, "checkpoint_id": checkpoint}
                             for decoder, checkpoint in zip(decoders, checkpoints))
    verify_report_goal("qec_compare", {**ARGS, "checkpoint_ids": checkpoints}, report)
