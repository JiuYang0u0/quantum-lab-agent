"""Check committed evidence bytes in fresh LF and Windows-style Git checkouts.

Run after committing: clones intentionally check HEAD, not uncommitted files.
No HTTP requests, model calls, or private source files are needed.
"""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def verify(root: Path) -> int:
    evidence = root / "docs/evidence"
    a2 = evidence / "a2-nvidia-20261008"
    expected = {
        a2 / name: digest
        for name, digest in json.loads((a2 / "manifest.json").read_text()).items()
    }
    artifacts = sorted((evidence / "a3-nvidia-web-20261009/quantum-artifacts").glob("*.json"))
    assert artifacts, "Missing A3 content-addressed artifacts"
    expected.update({path: path.stem for path in artifacts})
    for path, digest in expected.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == digest, f"{path.relative_to(root)}: {actual} != {digest}"
    return len(expected)


def main() -> None:
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="qla-evidence-checkouts-") as temporary:
        for autocrlf in ("false", "true"):
            checkout = Path(temporary) / autocrlf
            subprocess.run([
                "git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
                str(source), str(checkout),
            ], check=True)
            subprocess.run([
                "git", "-C", str(checkout), "config", "core.autocrlf", autocrlf,
            ], check=True)
            subprocess.run([
                "git", "-C", str(checkout), "checkout", "--quiet", "HEAD",
            ], check=True)
            count = verify(checkout)
            print(f"PASS: core.autocrlf={autocrlf}: {count} archived SHA-256 checks")


if __name__ == "__main__":
    main()
