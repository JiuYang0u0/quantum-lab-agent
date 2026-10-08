"""Launch only our isolated B process; always terminate its process tree on Windows."""
import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--b-repo", type=Path, required=True)
    parser.add_argument("--with-model", action="store_true")
    parser.add_argument("--minimal-probe", action="store_true")
    parser.add_argument("--multistep", action="store_true")
    parser.add_argument("--configured", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=6)
    parser.add_argument("--seconds", type=int, choices=range(180, 901), default=300)
    parser.add_argument("--finalize-on-report", action="store_true")
    args = parser.parse_args()
    if args.configured and (args.multistep or args.minimal_probe or args.with_model or not args.output):
        parser.error("--configured requires --output and excludes other model modes")
    if args.multistep and (args.minimal_probe or args.with_model or not args.output):
        parser.error("--multistep requires --output and excludes other model modes")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 18000))  # Fail rather than reuse someone else's server.
    temp_root = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "opencode"
    temp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="qla-b-", dir=temp_root))
    env = dict(os.environ, QEC_ARTIFACT_ROOT=str(root / "artifacts"),
               PYTHONPATH=str(args.b_repo / "src"), PYTHONDONTWRITEBYTECODE="1")
    python = args.b_repo / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    print(f"Isolated B artifacts/log: {root}", flush=True)
    with (root / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(python), "-m", "uvicorn", "qec_core.service.app:create_app",
                                    "--factory", "--host", "127.0.0.1", "--port", "18000"],
                                   cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(90):
                if process.poll() is not None:
                    raise RuntimeError(f"B exited; see {root / 'server.log'}")
                try:
                    if httpx.get("http://127.0.0.1:18000/api/health", timeout=1, trust_env=False).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("B readiness timeout")
            command = [sys.executable, str(Path(__file__).with_name(
                "configured_eval.py" if args.configured else
                "multistep_eval.py" if args.multistep else
                "minimal_tool_probe.py" if args.minimal_probe else "live_eval.py"))]
            if args.multistep:
                command.extend(["--output", args.output, "--max-tokens", str(args.max_tokens),
                                "--max-steps", str(args.max_steps), "--seconds", str(args.seconds)])
                if args.finalize_on_report:
                    command.append("--finalize-on-report")
            if args.with_model:
                command.append("--with-model")
            if args.configured:
                command.extend(["--output", args.output, "--max-steps", str(args.max_steps),
                                "--seconds", str(args.seconds)])
            subprocess.run(command, check=True, timeout=args.seconds + 240 if args.configured
                           else args.seconds + 60 if args.multistep else 360)
        finally:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False)
            else:
                process.terminate()
            process.wait(timeout=15)
    print(f"Owned B process stopped; evidence retained at {root}")


if __name__ == "__main__":
    main()
