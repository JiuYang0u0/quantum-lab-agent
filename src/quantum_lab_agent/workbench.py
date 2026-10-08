"""Local, single-process workbench. Durable jobs wrap the existing bounded Agent."""
import asyncio
import hashlib
import json
import os
import re
import stat
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import Field, model_validator

from .provider import Provider, Settings
from .runtime import Agent, Finalization, Limits, Trace, replay
from .schemas import Config


class RunRequest(Config):
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    family: Literal["qec", "quantum"]
    prompt: str = Field(min_length=1, max_length=8000)
    limits: Limits = Field(default_factory=Limits)
    reports: int = Field(default=0, ge=0, le=30)

    @model_validator(mode="after")
    def valid_goal(self):
        if not self.prompt.strip() or (self.family == "quantum" and self.reports):
            raise ValueError("quantum does not support QEC report goals; prompt required")
        return self


class BoundTrace(Trace):
    def start(self, prompt):
        return self.run_id


def create_app(*, settings=None, root=None, profile="lmstudio", model_factory=None,
               transport=None, fixture=False):
    if settings is None:
        load_dotenv()
        profile = os.getenv("QLA_PROFILE", profile)
        settings = Settings.load(profile)
    root = Path(root or os.getenv("QLA_WORKBENCH_ROOT", ".qla/workbench"))
    origins = ["http://127.0.0.1:5174", "http://localhost:5174",
               "http://127.0.0.1:8100", "http://localhost:8100"]
    worker = None

    @asynccontextmanager
    async def lifespan(app):
        trace = Trace(root / "trace.sqlite3", (settings.api_key, settings.qec_url,
                                                settings.base_url))
        trace.db.execute("CREATE TABLE IF NOT EXISTS web_mode(mode TEXT PRIMARY KEY)")
        mode = "fixture" if fixture else "production"
        prior_mode = trace.db.execute("SELECT mode FROM web_mode").fetchone()
        if prior_mode and prior_mode[0] != mode:
            trace.db.close()
            raise ValueError("workbench mode mismatch: use a separate data root")
        with trace.db:
            trace.db.execute("INSERT OR IGNORE INTO web_mode VALUES(?)", (mode,))
        trace.db.execute("""CREATE TABLE IF NOT EXISTS web_runs(
            id TEXT PRIMARY KEY, request TEXT, status TEXT, created REAL)""")
        trace.db.execute("""CREATE TABLE IF NOT EXISTS web_request_digests(
            id TEXT PRIMARY KEY, digest TEXT NOT NULL)""")
        with trace.db:
            trace.db.execute("UPDATE web_runs SET status='interrupted' "
                             "WHERE status IN ('queued','running')")
        app.state.trace = trace
        yield
        if worker and worker.is_alive():
            await asyncio.to_thread(worker.join, 2)
        with trace.db:
            trace.db.execute("UPDATE web_runs SET status='interrupted' "
                             "WHERE status IN ('queued','running')")
        trace.db.close()

    app = FastAPI(title="Quantum Lab Agent A3", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.headers.get("origin") and request.headers["origin"] not in origins:
            return Response(status_code=403)
        if request.url.hostname not in ("localhost", "127.0.0.1", "testserver"):
            return Response(status_code=403)
        if request.method == "POST":
            body = await request.body()
            if len(body) > 40000:
                return Response(status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def trace():
        return app.state.trace

    def row(identity):
        item = trace().db.execute("SELECT id,request,status,created FROM web_runs WHERE id=?",
                                  (identity,)).fetchone()
        if not item:
            raise HTTPException(404, "unknown run")
        request = json.loads(item[1])
        return {"run_id": item[0], "family": request["family"], "prompt": request["prompt"],
                "status": item[2], "created": item[3], "fixture": fixture}

    def exported(identity):
        row(identity)
        return trace().clean(trace().export(identity))

    async def execute_run(request):
        t = BoundTrace(root / "trace.sqlite3", (settings.api_key, settings.qec_url,
                                                settings.base_url))
        t.run_id = request.request_id
        status = "internal_error"
        try:
            async with httpx.AsyncClient(transport=transport) as client:
                model = model_factory(client) if model_factory else Provider(client, settings)
                outcome = await Agent(model, client, settings.qec_url, t,
                                      limits=request.limits,
                                      finalization=Finalization(reports=request.reports),
                                      family=request.family, quantum_root=root / "quantum").run(
                                          request.prompt)
                status = outcome["status"]
        except Exception:  # noqa: BLE001 -- worker boundary: persist failure without leaking secrets
            t.event(request.request_id, "server_error", {"error": "internal worker failure"})
        finally:
            with t.db:
                t.db.execute("UPDATE web_runs SET status=? WHERE id=? AND status='running'",
                             (status, request.request_id))
            t.db.close()

    @app.get("/api/config")
    async def config():
        return trace().clean({"profile": profile, "model": settings.model,
                              "max_tokens": settings.max_tokens, "fixture": fixture,
                              "defaults": Limits().model_dump(),
                              "bounds": {"max_steps": 30, "max_tools": 30, "seconds": 1800}})

    @app.post("/api/runs", status_code=202)
    async def submit(request: RunRequest):
        nonlocal worker
        normalized = json.dumps(trace().clean(request.model_dump()), sort_keys=True)
        digest = hashlib.sha256(json.dumps(request.model_dump(), sort_keys=True,
                                          separators=(",", ":")).encode()).hexdigest()
        prior = trace().db.execute("SELECT d.digest FROM web_runs r LEFT JOIN "
                                   "web_request_digests d ON r.id=d.id WHERE r.id=?",
                                   (request.request_id,)).fetchone()
        if prior:
            # Legacy sanitized rows cannot prove original identity: fail closed.
            if prior[0] != digest:
                raise HTTPException(409, "request ID already bound to another request")
            return row(request.request_id)
        if worker and worker.is_alive():
            raise HTTPException(409, "one active Agent allowed")
        with trace().db:
            trace().db.execute("INSERT INTO web_runs VALUES(?,?,?,?)",
                               (request.request_id, normalized, "running", time.time()))
            trace().db.execute("INSERT INTO web_request_digests VALUES(?,?)",
                               (request.request_id, digest))
            trace().db.execute("INSERT INTO runs VALUES(?,?,?)",
                               (request.request_id, time.time(), trace().clean(request.prompt)))
        worker = threading.Thread(target=lambda: asyncio.run(execute_run(request)), daemon=True)
        worker.start()
        return row(request.request_id)

    @app.get("/api/runs")
    async def history():
        return [row(r[0]) for r in trace().db.execute(
            "SELECT id FROM web_runs ORDER BY created DESC LIMIT 100")]

    @app.get("/api/runs/{identity}")
    async def detail(identity: str):
        item = row(identity)
        data = exported(identity)
        return {**item, "events": data["events"], "grounded_output": replay(data)}

    @app.get("/api/runs/{identity}/events")
    async def events(identity: str, after: int = Query(default=0, ge=0)):
        return {"status": row(identity)["status"], "events": [
            e for e in exported(identity)["events"] if e["seq"] > after]}

    @app.get("/api/runs/{identity}/export.json")
    async def export_json(identity: str):
        return {**exported(identity), "workbench": row(identity)}

    @app.get("/api/runs/{identity}/export.md")
    async def export_md(identity: str):
        item = row(identity)
        text = (f"# Quantum Lab Agent\n\nRun: {identity}\n\n"
                f"Family: {item['family']} / Status: {item['status']}\n\n"
                f"Fixture: {fixture}\n\n## Grounded evidence\n\n" + replay(exported(identity)))
        return Response(text, media_type="text/markdown")

    @app.get("/api/runs/{identity}/graphics/{filename}")
    async def graphic(identity: str, filename: str):
        data = exported(identity)
        if not re.fullmatch(r"[a-f0-9]{64}\.(png|svg)", filename):
            raise HTTPException(404)
        allowed = []
        for event in data["events"]:
            result = event["data"].get("result", {})
            if event["kind"] == "tool_result" and result.get("kind") == "quantum_plots":
                allowed.extend(result.get("graphics", {}).values())
        if not any(g.get("file") == filename and g.get("sha256") == filename[:64]
                   for g in allowed):
            raise HTTPException(404)
        path = root / "quantum" / filename
        try:
            absolute = path.absolute()
            for component in (absolute, *absolute.parents):
                metadata = component.lstat()
                if (stat.S_ISLNK(metadata.st_mode) or
                        getattr(metadata, "st_file_attributes", 0) &
                        stat.FILE_ATTRIBUTE_REPARSE_POINT):
                    raise ValueError("linked artifact ancestor")
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
                raise ValueError("artifact outside root")
            content = resolved.read_bytes()
        except (OSError, ValueError):
            raise HTTPException(404)
        if hashlib.sha256(content).hexdigest() != filename[:64]:
            raise HTTPException(409, "graphic hash mismatch")
        return Response(content, media_type="image/png" if filename.endswith("png") else
                        "image/svg+xml", headers={"Content-Security-Policy": "sandbox"})

    return app
