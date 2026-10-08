import asyncio
import hashlib
import json
import time

import pytest
from qiskit import transpile

from quantum_lab_agent.quantum import (
    BASIS,
    QuantumAdapter,
    circuit,
    render_quantum_report,
    resources,
)
from quantum_lab_agent.quantum_types import BuildCircuit, Simulation
from quantum_lab_agent.runtime import Agent, Finalization, Limits, Trace, render_report
from quantum_lab_agent.schemas import tool_schemas


def call(adapter, name, args):
    return asyncio.run(adapter.execute(name, args, time.monotonic() + 60))


def build(adapter, **kw):
    return call(adapter, "build_circuit", {"target": "bell", "preset": "bell", **kw})


def simulate(adapter, built, **kw):
    return call(adapter, "run_simulation", {"circuit_id": built["artifact_id"], **kw})


@pytest.mark.parametrize("n", [2, 3, 6])
def test_analytic_targets(tmp_path, n):
    adapter = QuantumAdapter(tmp_path)
    b = build(adapter, target="ghz", preset="ghz", qubits=n)
    assert b["verification"]["status"] == "verified"
    r = simulate(adapter, b)
    assert r["premeasurement_fidelity"] == pytest.approx(1)
    assert set(r["counts"]) == {"0" * n, "1" * n}
    assert sum(r["counts"].values()) == 1024


def test_phase_counts_and_asymmetric_bitorder(tmp_path):
    a = QuantumAdapter(tmp_path)
    good = simulate(a, build(a))
    bad = build(a, preset=None, gates=[{"name": "h", "qubits": [0]},
                                     {"name": "cx", "qubits": [0, 1]},
                                     {"name": "z", "qubits": [0]}])
    wrong = simulate(a, bad)
    assert bad["verification"]["status"] == "target_mismatch"
    assert wrong["counts"] == good["counts"]
    assert wrong["premeasurement_fidelity"] == pytest.approx(0, abs=1e-14)
    asymmetric = build(a, preset=None, gates=[{"name": "x", "qubits": [0]}])
    assert simulate(a, asymmetric)["counts"] == {"01": 1024}


@pytest.mark.parametrize("overrides", [
    {"qubits": 1}, {"qubits": 7}, {"qubits": True}, {"target": "arbitrary"},
    {"gates": []}, {"threshold": 0},
    {"preset": None, "gates": [{"name": "cx", "qubits": [0, 0]}]},
    {"preset": None, "gates": [{"name": "x", "qubits": [2]}]},
    {"preset": None, "gates": [{"name": "rx", "qubits": [0], "angle": float("nan")}]},
    {"preset": None, "gates": [{"name": "rz", "qubits": [0], "angle": float("inf")}]},
    {"preset": None, "gates": [{"name": "eval", "qubits": [0]}]},
    {"preset": None, "gates": [{"name": "h", "qubits": [0]}] * 65},
])
def test_bounds(overrides):
    with pytest.raises(ValueError):
        BuildCircuit.model_validate({"target": "bell", "preset": "bell", **overrides})


def test_noise(tmp_path):
    a = QuantumAdapter(tmp_path)
    b = build(a)
    ideal = simulate(a, b)
    zero = simulate(a, b, mode="noisy")
    readout = simulate(a, b, mode="noisy", noise={"readout": 0.3})
    noisy = simulate(a, b, mode="noisy", noise={"depolarizing_1q": 0.02,
                                               "depolarizing_2q": 0.04})
    assert zero["density_matrix"] == ideal["density_matrix"]
    assert zero["counts"] == ideal["counts"]
    assert readout["premeasurement_fidelity"] == ideal["premeasurement_fidelity"]
    assert set(readout["counts"]) == {"00", "01", "10", "11"}
    assert noisy["premeasurement_fidelity"] == pytest.approx(0.9604)
    assert noisy["verification"]["status"] == "verified"


def test_store_reports_resources_plots(tmp_path):
    a = QuantumAdapter(tmp_path)
    b = build(a)
    assert build(a)["artifact_id"] == b["artifact_id"]
    r = simulate(a, b)
    report = call(a, "quantum_read_report", {"result_id": r["artifact_id"]})
    assert "not inferred from counts" in report["rendered"]
    assert report["rendered"] == render_quantum_report(r)
    with pytest.raises(ValueError):
        render_report(report)
    with pytest.raises(ValueError):
        render_quantum_report({**r, "premeasurement_fidelity": 0})
    compiled = transpile(circuit(BuildCircuit(target="bell", preset="bell")),
                         basis_gates=BASIS, optimization_level=0, seed_transpiler=7)
    assert r["resources"]["gate_counts"] == dict(compiled.count_ops())
    assert r["resources"]["gate_counts"] == {"rz": 2, "sx": 1, "cx": 1}
    plots = call(a, "plot", {"result_id": r["artifact_id"]})
    for graphic in plots["graphics"].values():
        data = (tmp_path / graphic["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == graphic["sha256"]
    (tmp_path / f"{r['artifact_id']}.json").write_text("{}")
    with pytest.raises(ValueError):
        call(a, "quantum_read_report", {"result_id": r["artifact_id"]})
    with pytest.raises(ValueError):
        call(a, "verify", {"circuit_id": "../secrets"})


def test_limits_and_family(tmp_path):
    a = QuantumAdapter(tmp_path)
    build(a)
    with pytest.raises(ValueError):
        build(a, target="ghz", preset="ghz", qubits=3)
    build(a)
    build(a)
    with pytest.raises(ValueError):
        build(a)
    with pytest.raises(ValueError):
        call(a, "qec_list_artifacts", {})
    for kw in ({"shots": 8193}, {"seed": -1}, {"noise": {"readout": 0.2}}):
        with pytest.raises(ValueError):
            Simulation(circuit_id="a" * 64, **kw)
    assert all(t["function"]["name"].startswith("qec_") for t in tool_schemas())
    with pytest.raises(ValueError):
        Agent(None, None, "", Trace(tmp_path / "t.db"), family="quantum",
              finalization=Finalization(reports=1))


def test_agent_repair(tmp_path):
    class Fake:
        async def complete(self, messages, tools, deadline):
            assert {t["function"]["name"] for t in tools} == {
                "build_circuit", "verify", "run_simulation", "analyze", "plot", "quantum_read_report"}
            results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
            if not results:
                args = {"target": "bell", "gates": []}
            elif len(results) == 1:
                assert results[-1]["verification"]["status"] == "target_mismatch"
                args = {"target": "bell", "preset": "bell"}
            else:
                assert results[-1]["verification"]["status"] == "verified"
                return {"role": "assistant", "content": "done"}
            return {"role": "assistant", "tool_calls": [{"id": str(len(results)),
                    "type": "function", "function": {"name": "build_circuit",
                    "arguments": json.dumps(args)}}]}
    trace = Trace(tmp_path / "trace.db")
    result = asyncio.run(Agent(Fake(), None, "", trace, Limits(max_tools=3),
                               family="quantum", quantum_root=tmp_path / "artifacts").run("Bell"))
    assert result["status"] == "completed"
    assert result["tools_used"] == 2


def test_resource_rotation_translation():
    spec = BuildCircuit(target="bell", gates=[
        {"name": "ry", "qubits": [0], "angle": 0.2}, {"name": "cz", "qubits": [0, 1]}])
    result = resources(circuit(spec))
    assert set(result["gate_counts"]) <= set(BASIS)
    assert result["two_qubit_gates"] == 1


def test_work_off_event_loop(tmp_path, monkeypatch):
    import threading
    adapter = QuantumAdapter(tmp_path)
    caller = threading.get_ident()
    original = adapter.work

    def checked(name, args):
        assert threading.get_ident() != caller
        return original(name, args)

    monkeypatch.setattr(adapter, "work", checked)
    build(adapter)


def test_agent_cannot_claim_uncorrected_target(tmp_path):
    class Wrong:
        async def complete(self, messages, tools, deadline):
            if any(m["role"] == "tool" for m in messages):
                return {"role": "assistant", "content": "success"}
            return {"role": "assistant", "tool_calls": [{"id": "wrong", "type": "function",
                    "function": {"name": "build_circuit", "arguments":
                                 json.dumps({"target": "bell", "gates": []})}}]}

    result = asyncio.run(Agent(Wrong(), None, "", Trace(tmp_path / "trace.db"),
                               family="quantum", quantum_root=tmp_path / "store").run("Bell"))
    assert result["status"] == "target_mismatch"


class ScriptedQuantumModel:
    def __init__(self, actions):
        self.actions = iter(actions)

    async def complete(self, messages, tools, deadline):
        action = next(self.actions, None)
        if action is None:
            return {"role": "assistant", "content": "done"}
        name, args = action
        return {"role": "assistant", "tool_calls": [{"id": str(len(messages)),
                "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


@pytest.mark.parametrize("tool", ["run_simulation", "quantum_read_report", "analyze", "plot"])
@pytest.mark.parametrize("success_position", ["none", "before", "after"])
def test_persisted_mismatch_remains_relevant(tmp_path, tool, success_position):
    root = tmp_path / "store"
    old = QuantumAdapter(root)
    bad = build(old, preset=None, gates=[])
    report = simulate(old, bad)
    assert report["premeasurement_fidelity"] == pytest.approx(0.5)
    args = ({"result_id": report["artifact_id"]} if tool in ("plot", "quantum_read_report")
            else {"circuit_id": bad["artifact_id"]})
    actions = [(tool, args)]
    good_build = ("build_circuit", {"target": "bell", "preset": "bell"})
    if success_position == "before":
        actions.insert(0, good_build)
    elif success_position == "after":
        actions.append(good_build)
    result = asyncio.run(Agent(ScriptedQuantumModel(actions), None, "",
                               Trace(tmp_path / "trace.db"), family="quantum",
                               quantum_root=root).run("Use stored circuit"))
    assert result["status"] == "target_mismatch"


@pytest.mark.parametrize("tool", ["run_simulation", "quantum_read_report"])
def test_persisted_valid_noisy_circuit_can_complete(tmp_path, tool):
    root = tmp_path / "store"
    old = QuantumAdapter(root)
    good = build(old)
    config = {"circuit_id": good["artifact_id"], "mode": "noisy",
              "noise": {"depolarizing_2q": 1.0}}
    report = call(old, "run_simulation", config)
    assert report["premeasurement_fidelity"] == pytest.approx(0.25)
    args = config if tool == "run_simulation" else {"result_id": report["artifact_id"]}
    result = asyncio.run(Agent(ScriptedQuantumModel([(tool, args)]), None, "",
                               Trace(tmp_path / "trace.db"), family="quantum",
                               quantum_root=root).run("Use noisy circuit"))
    assert result["status"] == "completed"


@pytest.mark.parametrize("tool", ["run_simulation", "quantum_read_report"])
def test_cli_persisted_mismatch_nonzero(tmp_path, monkeypatch, tool):
    from quantum_lab_agent import cli
    from quantum_lab_agent.provider import Settings
    root = tmp_path / "store"
    old = QuantumAdapter(root)
    bad = build(old, preset=None, gates=[])
    report = simulate(old, bad)
    args = ({"circuit_id": bad["artifact_id"]} if tool == "run_simulation"
            else {"result_id": report["artifact_id"]})
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(Settings, "load", lambda profile: Settings())
    monkeypatch.setattr(cli, "Provider", lambda *a: ScriptedQuantumModel([(tool, args)]))
    monkeypatch.setattr("sys.argv", ["qla", "--trace-db", str(tmp_path / "cli.db"),
                                   "run", "--family", "quantum", "--artifact-root", str(root),
                                   "--prompt", "Use stored circuit"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
