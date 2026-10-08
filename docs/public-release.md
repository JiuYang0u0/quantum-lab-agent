# Public snapshot preparation

## Provenance and publication status

This clean public copy was exported with `git archive HEAD` from source commit
`434f99e34f49941e6b4f949f2f6b90aafa362260`. Only tracked snapshot content was
exported. The original repository and its unsanitized historical records remain
private and unchanged. Public history starts with one truthful snapshot commit;
it does not reconstruct or import private development history.

Intended repository: https://github.com/JiuYang0u0/quantum-lab-agent.
This is an intended location, not a claim that hosting, push, hosted CI, a release,
or registry publication has occurred. Independent parent review gates publishing.

## Public sanitization mapping

Windows user-profile components in historical transport paths were replaced by
the literal generic placeholder `PUBLIC_USER`, preserving separators and JSON
escaping. Original identifying values are deliberately not recorded here.
Paths are archival descriptions, not required local paths or instructions.

Six evidence files changed only through this mapping (16 substitutions total):

- `evidence/gemma-finalize-report-900-launch.txt` (6)
- `evidence/gemma-finalize-report-900.md` (3)
- `evidence/gemma-multistep-900.md` (3)
- `evidence/gemma-multistep.md` (1)
- `evidence/nvidia-configured-provenance.json` (1)
- `evidence/nvidia-configured.md` (2)

Scientific numerical results, seeds, timings, experiment IDs, original failure
conclusions, scientific artifact bytes, and associated scientific hashes are
unchanged. The configured provenance JSON changes only its `artifact_root`
transport prefix; its metadata and artifact SHA-256 map are unchanged. No changed
file is covered by the A2 artifact manifest, so no manifest regeneration was
needed. The existing Web verifier already resolves its evidence relative to its
own file; no verifier weakening or path workaround was needed.

The historical README at `legacy-usage.md` has eleven relative links repaired.
Preservation statements in the evidence index, project structure, reproducibility,
and release-readiness documents now distinguish private originals from sanitized
public copies. Historical source-stage counts in release-readiness describe that
earlier verification, not this public copy's byte identity.

Git and Docker ignore rules now cover dotenv variants (retaining `.env.example`),
SQLite/database state and sidecars, private key files, and common credential files.
Both stored browser screenshots were visually reviewed; no personal filesystem
path was visible, so their original image bytes were retained.

## Fresh local verification

Verification used a fresh isolated temporary uv environment, disabled dotenv
loading, and removed provider-key/secret environment variables. Dependency installs
used package registries. Tests and stored-evidence verification were offline: no
live provider, QPU, or external B jobs were invoked, and no private `.env` was read.

| Check | Result |
|---|---|
| `uv sync --locked` | 44 packages installed; lock unchanged; CPython 3.12.13 |
| `uv run --locked pytest -q` | 235 passed; one existing Starlette/httpx deprecation warning |
| `uv run --locked ruff check .` | Passed |
| Stored Web `verify.py` | Passed scoped Bell science, QEC v2 native/job bindings, grounded exports, seven completions |
| `uv build` | Source distribution and wheel built |
| `npm ci` | Passed; zero audit vulnerabilities reported at this invocation |
| `npm test` | 6 tests passed |
| `npm run build` | TypeScript and Vite production build passed |

Apache-2.0 licensing and existing citations are retained. The canonical license
SHA-256 is `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`.
Package contents, relative Markdown links, privacy patterns, and snapshot integrity
were checked locally: 193 relative Markdown links resolved; both package formats
include the canonical license and SPDX metadata and exclude private runtime data.
The source-archive comparison confirmed the six evidence changes are exactly the
documented profile substitutions. These are local results, not hosted-CI
or cross-platform execution claims.
