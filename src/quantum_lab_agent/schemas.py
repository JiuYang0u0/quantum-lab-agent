"""Small explicit subset of B's CPU service contract; never import B."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")]
Seed = Annotated[int, Field(ge=0, le=2**63 - 1)]


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Circuit(Config):
    code: Literal["repetition", "surface"] = "repetition"
    distance: Literal[3, 5, 7] = 3
    rounds: int = Field(default=3, ge=1, le=10)
    p: float = Field(default=0.03, ge=0, le=1)
    seed: Seed = 42

    @model_validator(mode="after")
    def supported(self):
        if self.code == "surface" and self.distance == 7:
            raise ValueError("surface distance must be 3 or 5")
        return self


class Sampling(Config):
    train_shots: int = Field(default=128, ge=1, le=8192)
    validation_shots: int = Field(default=32, ge=1, le=2048)
    test_shots: int = Field(default=64, ge=1, le=4096)


class Training(Config):
    architecture: Literal["mlp", "cnn"] = "mlp"
    epochs: int = Field(default=1, ge=1, le=30)
    patience: int = Field(default=1, ge=1, le=10)
    batch_size: int = Field(default=32, ge=16, le=256)
    hidden_size: int = Field(default=8, ge=4, le=64)
    learning_rate: float = Field(default=0.001, gt=0, le=1)
    seed: Seed = 123
    device: Literal["cpu"] = "cpu"
    threads: Literal[1] = 1


class Benchmark(Config):
    warmup: int = Field(default=0, ge=0, le=2)
    repeats: int = Field(default=1, ge=1, le=5)
    batch_size: int = Field(default=32, ge=16, le=256)
    device: Literal["cpu"] = "cpu"
    threads: Literal[1] = 1


class Sample(Config):
    circuit: Circuit = Field(default_factory=Circuit)
    sampling: Sampling = Field(default_factory=Sampling)


class Train(Config):
    dataset_id: ID
    training: Training = Field(default_factory=Training)


class Compare(Config):
    dataset_id: ID
    checkpoint_ids: list[ID] = Field(default_factory=list, max_length=4)
    benchmark: Benchmark = Field(default_factory=Benchmark)
    allow_cross_p: bool = False

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.checkpoint_ids)) != len(self.checkpoint_ids):
            raise ValueError("duplicate checkpoints")
        return self


class ReadReport(Config):
    result_id: ID


TOOLS = {
    "qec_list_artifacts": (Config, "List existing dataset, checkpoint and comparison artifacts."),
    "qec_sample": (Sample, "Submit small CPU sampling and wait for its dataset artifact."),
    "qec_train": (Train, "Train a CPU decoder on an existing dataset and wait for checkpoint."),
    "qec_compare": (Compare, "Compare MWPM, lookup and optional checkpoints; wait for report."),
    "qec_read_report": (ReadReport, "Read a validated comparison report by artifact ID."),
}


def validate_tool(name: str, arguments: dict) -> dict:
    if name not in TOOLS:
        raise ValueError("unknown tool")
    return TOOLS[name][0].model_validate(arguments).model_dump()


def tool_schemas(family="qec") -> list[dict]:
    if family == "quantum":
        from .quantum_types import QUANTUM_TOOLS
        registry = QUANTUM_TOOLS
    elif family == "qec":
        registry = TOOLS
    else:
        raise ValueError("unknown tool family")
    def inline(schema):
        # Some native chat templates do not resolve Pydantic's local $defs/$ref.
        # Our schemas are acyclic; retain every validation constraint when expanding.
        definitions = schema.get("$defs", {})

        def expand(value):
            if isinstance(value, list):
                return [expand(v) for v in value]
            if not isinstance(value, dict):
                return value
            if "$ref" in value:
                return expand({**definitions[value["$ref"].removeprefix("#/$defs/")],
                               **{k: v for k, v in value.items() if k != "$ref"}})
            return {k: expand(v) for k, v in value.items() if k != "$defs"}

        return expand(schema)

    return [{"type": "function", "function": {
        "name": name, "description": description, "parameters": inline(model.model_json_schema()),
    }} for name, (model, description) in registry.items()]
