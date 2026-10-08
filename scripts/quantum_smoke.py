"""Offline real Aer evidence; no provider, .env, HTTP, or credentials."""
import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path

from quantum_lab_agent.quantum import QuantumAdapter, render_quantum_report


async def smoke(root):
    root = Path(root)
    summary = []
    for target, qubits in [("bell", 2), ("ghz", 3)]:
        adapter = QuantumAdapter(root)

        async def call(name, args, adapter=adapter):
            return await adapter.execute(name, args, time.monotonic() + 120)

        built = await call("build_circuit", {"target": target, "preset": target, "qubits": qubits})
        assert built["verification"]["status"] == "verified"
        for label, noise in [("ideal", {}), ("readout", {"readout": 0.1}),
                             ("gate_noise", {"depolarizing_1q": 0.02, "depolarizing_2q": 0.04})]:
            result = await call("run_simulation", {"circuit_id": built["artifact_id"],
                                "mode": "ideal" if label == "ideal" else "noisy",
                                "noise": noise, "seed": 7, "shots": 1024})
            verified = await call("quantum_read_report", {"result_id": result["artifact_id"]})
            assert verified["rendered"] == render_quantum_report(result)
            assert sum(result["counts"].values()) == 1024
            if label != "gate_noise":
                assert abs(result["premeasurement_fidelity"] - 1) < 1e-12
            plots = await call("plot", {"result_id": result["artifact_id"]})
            for graphic in plots["graphics"].values():
                assert hashlib.sha256((root / graphic["file"]).read_bytes()).hexdigest() == graphic["sha256"]
            summary.append({"target": target, "case": label, "circuit_id": built["artifact_id"],
                            "result_id": result["artifact_id"], "plots_id": plots["artifact_id"],
                            "fidelity": result["premeasurement_fidelity"],
                            "counts": result["counts"], "resources": result["resources"]})
    (root / "smoke-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=".qla/quantum-smoke")
    asyncio.run(smoke(parser.parse_args().output))
