"""Offline evidence verification; no HTTP or model requests."""
import copy
import json
from pathlib import Path

from quantum_lab_agent.evaluation import assess
from quantum_lab_agent.qec_evidence import assess_bound_qec
from quantum_lab_agent.quantum_evaluation import assess_quantum, paired_execution
from quantum_lab_agent.runtime import replay

root = Path(__file__).parent
quantum = json.loads((root / "quantum-trace.json").read_text())
qec = json.loads((root / "qec-trace.json").read_text())
summary = json.loads((root / "summary.json").read_text())
pairs = paired_execution(quantum["events"])
assert [p[1] for p in pairs] == [
    "build_circuit", "verify", "run_simulation", "analyze", "quantum_read_report"]
assert pairs[3][2]["circuit_id"] == pairs[0][3]["artifact_id"]
assert pairs[3][3] == summary["cases"]["quantum"]["resources"]
strict = assess_quantum(quantum, root / "quantum-artifacts", "bell_ideal", replay(quantum))
assert strict == summary["cases"]["quantum"]["strict_historical_assessment"]
projected = copy.deepcopy(quantum)
projected["events"] = [e for e in projected["events"] if not (
    e["kind"] in ("tool_call", "tool_result") and e["data"]["tool"] == "analyze")]
for event in projected["events"]:
    if event["kind"] == "model":
        event["data"]["tool_calls"] = [c for c in event["data"].get("tool_calls", [])
                                       if c["function"]["name"] != "analyze"]
science = assess_quantum(projected, root / "quantum-artifacts", "bell_ideal", replay(quantum))
assert science == summary["cases"]["quantum"]["scientific_assessment"]
assert science["task_success"]
assert assess(qec) == summary["cases"]["qec"]["assessment"]
assert assess(qec)["task_success"]
bound = assess_bound_qec(qec)
assert bound["task_success"], bound["failures"]
count = 0
for family, trace in (("quantum", quantum), ("qec", qec)):
    assert not trace["workbench"]["fixture"]
    experiment = next(e["data"] for e in trace["events"] if e["kind"] == "experiment")
    assert experiment["limits"] == {"max_steps": 5, "max_tools": 5, "seconds": 300}
    calls = sum(e["kind"] == "model_metadata" for e in trace["events"])
    assert calls == summary["cases"][family]["completion_count"] <= 5
    count += calls
    assert replay(trace) in (root / f"{family}-report.md").read_text(encoding="utf-8")
assert count == summary["total_completions"] == 7
print("PASS: scoped Bell science, QEC v2 native/job bindings, grounded exports, seven completions")
