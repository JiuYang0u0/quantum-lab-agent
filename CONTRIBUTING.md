# Contributing

This is a local 0.1.0 preparation, not a published release. Start with the
[architecture](docs/architecture.md), [limitations](docs/limitations.md), and
[reproduction checks](docs/reproducibility.md).

Use Python 3.12, uv, and Node.js 22.12+; run `uv sync --locked` and `npm ci`
in `frontend`. Keep changes small and include a reproducible explanation.
Changes to scientific behavior need tests against an independent numeric oracle,
not only a copy of the implementation. Separate fixture checks from live evidence.

Before submitting, run the Python tests, Ruff, package build, frontend tests/build,
and evidence verifier listed in the reproduction guide. Explain any skipped check.
Do not run paid/provider evaluations as part of ordinary tests. Live evaluation
requires an explicit model, budget, and fresh output directory.

Preserve historical evidence, failures, artifact bytes, and hashes. Add a new
assessment instead of rewriting an old result. Never commit `.env`, credentials,
SQLite databases, raw `.qla` state, private datasets, or provider reasoning text.
Inspect sanitized exports before sharing: paths and prompts may still be sensitive.

Use the issue forms and pull-request template when this repository is hosted.
For sensitive findings see [SECURITY.md](SECURITY.md). Contributions are submitted
under the project's [Apache-2.0 license](LICENSE); retain third-party notices.
