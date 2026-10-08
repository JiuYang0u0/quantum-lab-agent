FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev
ENV QLA_WORKBENCH_ROOT=/data/workbench
CMD ["uv", "run", "--no-sync", "uvicorn", "quantum_lab_agent.workbench:create_app", "--factory", "--host", "0.0.0.0", "--port", "8100", "--workers", "1", "--timeout-graceful-shutdown", "5"]
