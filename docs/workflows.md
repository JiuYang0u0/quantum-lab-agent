# Workflows

## Local quantum, without an LLM

```sh
uv run python scripts/quantum_smoke.py --output .qla/quantum-smoke
uv run qla quantum-tool build_circuit --arguments '{"target":"bell","preset":"bell"}'
```

Pass the returned circuit hash to `verify`, `analyze`, or `run_simulation`; pass
the simulation hash to `quantum_read_report` or `plot`. See
[tool reference](tool-reference.md) for schemas and [A2 guide](a2-quantum.md)
for noise definitions. PowerShell versions that alter native JSON quoting can
use the smoke script instead.

## Model-directed quantum (live)

```sh
uv run qla run --family quantum --prompt "Build and verify Bell, simulate 1024 shots with seed 7, read the report." --max-tools 6 --max-steps 5 --seconds 300
```

This contacts the configured LLM but needs no B service. `completed` means model
termination, not validation of every natural-language objective. Scientific
success must be assessed from the artifacts.

## External QEC (live)

Start a compatible Project B service independently, set `QLA_QEC_URL`, and use:

```sh
uv run qla run --finalize-on-report --prompt "Use small CPU defaults to sample, train one MLP, compare, and deliver one report."
```

QEC is the CLI default family. `--finalize-on-report` declares a report-only goal;
`--report-count N` requires N distinct report IDs. Verified reports are delivered
without another model completion. General mode lets the model stop. Optional
`--interpret` permits only a constrained conceptual caveat, using separate
token/time limits; it is not free-form scientific interpretation. Full semantics
are preserved in [legacy usage](legacy-usage.md).

## Inspect and replay

```sh
uv run qla export <RUN_ID> --output .qla/run.json
uv run qla replay .qla/run.json
uv run qla replay docs/evidence/qec-integration.json
```

Global options precede subcommands: `qla --trace-db .qla/demo.sqlite3 run ...`.
Replay renders stored evidence without model calls or job submission. It does not
rerun an experiment. Exit codes: 0 completed/report_ready, 1 unsuccessful run or
budget/provider issue, 2 configuration/file error; inspect status and assessment
even when the process exits 0.

For Web submissions, retain the 32-hex request ID. Reconfirm uncertain submission
with the same ID and original payload; changed payload returns 409. A new ID is
a new experiment. An uncertain B POST is never automatically resent: inspect B's
job records first. Server restart marks unfinished Web runs `interrupted` rather
than resuming. Browser close and timeout do not guarantee cancellation.
