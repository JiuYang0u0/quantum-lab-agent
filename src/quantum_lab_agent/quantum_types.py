"""Closed local-circuit contract, without executable input or paths."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .schemas import Config

ArtifactID = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
TARGET_THRESHOLD = 0.999999


class Gate(Config):
    name: Literal["h", "x", "y", "z", "s", "sdg", "cx", "cz", "rx", "ry", "rz"]
    qubits: list[int] = Field(min_length=1, max_length=2)
    angle: float | None = None

    @model_validator(mode="after")
    def valid(self):
        if len(self.qubits) != (2 if self.name in ("cx", "cz") else 1):
            raise ValueError("gate arity mismatch")
        if len(set(self.qubits)) != len(self.qubits) or any(q < 0 for q in self.qubits):
            raise ValueError("invalid or repeated qubits")
        if (self.angle is not None) != (self.name in ("rx", "ry", "rz")):
            raise ValueError("rotation requires finite angle; other gates forbid angle")
        return self


class BuildCircuit(Config):
    qubits: int = Field(default=2, ge=2, le=6)
    target: Literal["bell", "ghz"]
    preset: Literal["bell", "ghz"] | None = None
    gates: list[Gate] | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def valid(self):
        if (self.preset is None) == (self.gates is None):
            raise ValueError("provide exactly one of preset or gates")
        if (self.target == "bell" or self.preset == "bell") and self.qubits != 2:
            raise ValueError("Bell requires two qubits")
        if any(q >= self.qubits for gate in self.gates or [] for q in gate.qubits):
            raise ValueError("qubit outside circuit")
        return self


class CircuitRef(Config):
    circuit_id: ArtifactID


class Noise(Config):
    depolarizing_1q: float = Field(default=0, ge=0, le=1)
    depolarizing_2q: float = Field(default=0, ge=0, le=1)
    readout: float = Field(default=0, ge=0, le=1)


class Simulation(CircuitRef):
    mode: Literal["ideal", "noisy"] = "ideal"
    noise: Noise = Field(default_factory=Noise)
    shots: int = Field(default=1024, ge=1, le=8192)
    seed: int = Field(default=7, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def valid(self):
        if self.mode == "ideal" and any(self.noise.model_dump().values()):
            raise ValueError("ideal mode forbids noise")
        return self


class ResultRef(Config):
    result_id: ArtifactID


QUANTUM_TOOLS = {
    "build_circuit": (BuildCircuit, "Build preset or restricted gates for fixed Bell/GHZ target. Three attempts maximum; target locked on first build."),
    "verify": (CircuitRef, "Verify ideal premeasurement fidelity against independent target, fixed threshold."),
    "run_simulation": (Simulation, "Local bounded Aer density-matrix evolution and finite-shot counts."),
    "analyze": (CircuitRef, "Exact resources in rz/sx/x/cx basis, all-to-all, optimization 0, seed 7."),
    "plot": (ResultRef, "Create circuit and histogram SVG/PNG artifacts from stored simulation."),
    "quantum_read_report": (ResultRef, "Read hash-verified quantum simulation with fixed renderer."),
}
