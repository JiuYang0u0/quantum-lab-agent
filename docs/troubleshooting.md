# Troubleshooting

| Symptom | Check / action |
|---|---|
| Install fails | Use Python 3.12 and current uv; retain `uv.lock`. Check wheel availability for your OS/architecture; Ubuntu CI is authored but not locally verified. |
| Frontend engine/build failure | Node >=22.12, `npm ci` in `frontend`; use the committed lockfile. |
| Port occupied | A uses 8100/5174. Stop only your own A process, or configure your own isolated environment; do not kill unrelated B/model services. |
| Wrong model after profile switch | Existing environment/`.env` URL and model override profile defaults; inspect locally, never paste keys into issues. |
| Model listed but no tools | `doctor` checks availability, not tool support. `doctor --probe-tools` makes live requests and needs an explicit budget. |
| Empty/length-limited output | Inspect finish reason and usage. Reasoning may consume `max_tokens`; increasing it changes cost/latency and does not guarantee success. |
| QEC unavailable | Quantum is independent of B; QEC needs B's HTTP service and matching `QLA_QEC_URL`. A does not install/start B automatically. |
| 409 on submission | One active Agent is allowed. Reuse an ID only with identical original payload; legacy requests without digests cannot be resubmitted. |
| Uncertain B POST | Inspect B job state using recorded IDs/intents. Do not blindly retry or create a replacement run. |
| Run interrupted after restart | Expected recovery policy; traces remain readable but work is not resumed automatically. |
| Graphic 404/409 | Only run-authorized, hash-valid files are served. Preserve damaged evidence and investigate; do not rewrite hashes to hide corruption. |
| Fixture banner / fixed behavior | You started the offline fixture factory; stop it and explicitly configure/start production for live runs. |
| `completed` but missing objective | Inspect grounded tools and scientific assessment; model termination is not proof of task success. |

For bug reports use a minimal sanitized reproduction, exact commit and versions,
fixture/live label, limits, and status. Do not attach `.env` or raw SQLite state.
See [contributing](../CONTRIBUTING.md).
