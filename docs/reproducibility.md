# Reproducibility

Record the Git commit, OS/Python/tool versions, exact model ID, limits, seeds,
noise, tool chain, artifact hashes, and evaluator version. Never infer model
reliability from a single successful run. Package installation may use network;
the following checks do not need model credentials or B:

```sh
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv build
uv run --locked python docs/evidence/a3-nvidia-web-20261009/verify.py
uv run --locked python scripts/quantum_smoke.py --output .qla/quantum-smoke
```

```sh
cd frontend
npm ci
npm test
npm run build
```

For a keyless verification environment set `PYTHON_DOTENV_DISABLED=1`, unset
provider credentials, and run only the offline commands above. CI does this;
neither `doctor` nor live scripts belong to the offline test suite.
To check a clean Python install, set `UV_PROJECT_ENVIRONMENT` to a fresh temporary
directory before `uv sync --locked` and use `uv run --locked` for the checks.

The [Web verifier](evidence/a3-nvidia-web-20261009/verify.py) checks the stored
Bell artifacts and QEC trace binding without APIs. It deliberately preserves the
historical strict Bell assessment failure and verifies a documented scoped chain.
See [evaluation](evaluation.md) and [public evidence index](evidence/README.md).

Hashes verify stored bytes, not independent authorship. Seeds improve local
repeatability; timings, provider behavior, generated plot metadata, and exact
floating-point behavior across versions/machines need not match. Archived local
absolute paths use generic public profile placeholders and are not required for
offline verification. See [public release provenance](public-release.md).

Live reproduction is separate: read each evidence README, install compatible B
if needed, use a fresh data/output root, explicitly configure model and budget,
and retain new evidence separately. It can cost money and is never an implicit
step in offline verification. Do not overwrite historical results.
