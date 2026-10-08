# Local 0.1.0 release readiness

## Distribution status

Version metadata is 0.1.0; the changelog remains **Unreleased**. This preparation
does not create a tag, release date, remote, push, hosted release, or registry
publication. GitHub workflow/templates are authored locally; **GitHub CI has not
been executed**. No passing-hosted-CI badge is claimed.

Python declares >=3.12; the locally checked baseline is CPython 3.12.13 on Windows.
The authored matrix targets Python 3.12 on Windows and Ubuntu. Locked scientific
dependencies include Linux wheels, but this session did not execute Linux, Docker,
or other Python versions. Node v24.11.1/npm 11.6.2 were used locally; CI targets
Node 22, consistent with the frontend's documented 22.12+ baseline.

## Original source verification (before public-copy sanitization)

- Fresh temporary environment: `uv sync --locked` with uv 0.11.7 installed 44
  packages; no lockfile update was needed for metadata-only packaging changes.
- `pytest -q`: **235 passed**, one existing Starlette/httpx deprecation warning.
- `ruff check .`: passed.
- `uv build`: source distribution and wheel built successfully.
- Stored Web evidence verifier: passed scoped Bell science, QEC v2 native/job
  bindings, grounded exports, and seven-completion accounting.
- Local quantum smoke: six Bell/GHZ ideal/readout/gate-noise cases passed with
  report and plot artifacts in a temporary output root.
- `npm ci`: installed successfully, audit reported zero vulnerabilities at this
  invocation; this is not a perpetual security guarantee.
- Frontend: **6 tests passed**; TypeScript/Vite production build passed.
- Original source documentation/package inspection: **159 new relative links**
  resolved; **67 pre-existing `docs/` Git blobs, including 60 under
  `docs/evidence/`,** were unchanged there (checkout EOL filters respected).
  The archived README matched original bytes at that stage. These are original
  source preservation counts, not byte-preservation claims for this public copy.
- Canonical license bytes and SPDX/readme metadata were checked in both package
  formats; the source archive excludes `.env`, `.qla`, and SQLite state.

Verification used `PYTHON_DOTENV_DISABLED=1` and an empty provider-key environment.
No live provider calls, B jobs, `.env` inspection, or knowledge-base edits were
part of this preparation. Fresh environments/artifacts reside outside the repo;
generated dist files and frontend build products are ignored.

## Licensing and provenance

[LICENSE](../LICENSE) is the complete canonical Apache-2.0 text fetched from
https://www.apache.org/licenses/LICENSE-2.0.txt. Its SHA-256 is
`cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`.
Copyright attribution uses the existing Git author **JiuYang**, without inventing
a legal name, DOI, repository URL, or release date. License metadata is SPDX
`Apache-2.0`, and package builds include the license file.

The prior root README is archived in [legacy-usage.md](legacy-usage.md), with
eleven relative links repaired for its public location. Public evidence replaces
personal profile names in transport paths; scientific data, historical conclusions,
and scientific hashes are unchanged. Original raw records remain private in the
source repository. See [public release preparation](public-release.md) for fresh
copy verification and the [public evidence index](evidence/README.md) for boundaries.

## Remaining release decisions

Independent parent review is still required. Hosted CI/platform execution,
private reporting contact, hosting location, tagging, and publication are future
maintainer decisions. See [roadmap](roadmap.md) and [security](../SECURITY.md).
