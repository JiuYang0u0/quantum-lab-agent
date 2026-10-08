"""Content-addressed JSON and graphics in an operator-owned local root."""
import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter

from .quantum_types import ArtifactID


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class QuantumStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, value):
        data = canonical(value)
        identity = hashlib.sha256(data).hexdigest()
        (self.root / f"{identity}.json").write_bytes(data)
        return {"artifact_id": identity, **value}

    def get(self, identity, kind):
        TypeAdapter(ArtifactID).validate_python(identity)
        data = (self.root / f"{identity}.json").read_bytes()
        if hashlib.sha256(data).hexdigest() != identity:
            raise ValueError("artifact fingerprint mismatch")
        value = json.loads(data)
        if value.get("kind") != kind:
            raise ValueError("artifact family/type mismatch")
        return {"artifact_id": identity, **value}

    def graphic(self, data, extension):
        if extension not in ("svg", "png"):
            raise ValueError("unsupported graphic")
        identity = hashlib.sha256(data).hexdigest()
        name = f"{identity}.{extension}"
        (self.root / name).write_bytes(data)
        return {"sha256": identity, "file": name}
