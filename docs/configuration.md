# Configuration

Actual settings: [provider.py](../src/quantum_lab_agent/provider.py),
[CLI](../src/quantum_lab_agent/cli.py), [workbench](../src/quantum_lab_agent/workbench.py).
The checked-in [provider profiles](../config/providers.toml) document defaults;
they are **not** an arbitrary TOML configuration loader.

| Variable | Default / meaning |
|---|---|
| `QLA_PROFILE` | `lmstudio`; or `nvidia` |
| `QLA_BASE_URL` | LM Studio `http://127.0.0.1:1234/v1`; NVIDIA `https://integrate.api.nvidia.com/v1` |
| `QLA_MODEL` | LM Studio `google/gemma-4-e2b`; NVIDIA requires an explicit exact model ID |
| `QLA_API_KEY` | Empty; server-side provider credential |
| `QLA_QEC_URL` | `http://127.0.0.1:8000`; external B |
| `QLA_MAX_TOKENS` | 512; range 16–2048, may include reasoning tokens |
| `QLA_TRACE_DB` | CLI `.qla/trace.sqlite3` |
| `QLA_WORKBENCH_ROOT` | Production `.qla/workbench` |
| `QLA_FIXTURE_ROOT` | Fixture `.qla/acceptance-fixture` |
| `QLA_CONTAINER_QEC_URL` | Compose B URL override; see [compose.yaml](../compose.yaml) |

CLI and production factory load local `.env`; existing environment values take
precedence. Copy `.env.example` only if `.env` does not already exist. Never
commit the resulting file. Set credentials privately in your shell/environment.
Changing profile does not override existing URL/model environment or `.env` values.
URLs must be HTTP(S), with no embedded credentials, query, or fragment.

PowerShell example (live, may incur provider cost):

```powershell
$env:QLA_PROFILE = 'nvidia'
$env:QLA_BASE_URL = 'https://integrate.api.nvidia.com/v1'
$env:QLA_MODEL = '<exact model ID available to your account>'
$env:QLA_MAX_TOKENS = '2048'
```

POSIX shells use `export QLA_PROFILE=nvidia` and equivalent assignments. No key
belongs in browser configuration. The UI only calls `/api`; Vite proxies to 8100.
Default A ports are API 8100/UI 5174, separate from B 8000/5173.

Agent defaults: 6 model steps, 5 tool attempts, 120 seconds. Web bounds are
30 steps, 30 tools, 1800 seconds. Failed/invalid tools consume budget. QEC report
goals allow 0–30 (0 means general mode); Quantum requires 0.
