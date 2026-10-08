# Local API reference

Implementation: [workbench.py](../src/quantum_lab_agent/workbench.py).
Interactive schema: `http://127.0.0.1:8100/docs`; JSON schema: `/openapi.json`.
One worker, one instance per root. Requests require an allowed localhost host
and, when supplied, allowed local origin; there is no user authentication.

| Method | Route | Response |
|---|---|---|
| GET | `/api/config` | Redacted profile/model, fixture flag, default limits/bounds |
| POST | `/api/runs` | 202 run metadata; 409 conflict/busy; 422 schema failure |
| GET | `/api/runs` | Latest 100 run metadata records |
| GET | `/api/runs/{id}` | Metadata, complete events, grounded output |
| GET | `/api/runs/{id}/events?after=0` | Status and events after persisted sequence cursor |
| GET | `/api/runs/{id}/export.json` | Redacted trace plus workbench metadata |
| GET | `/api/runs/{id}/export.md` | Deterministically rendered Markdown |
| GET | `/api/runs/{id}/graphics/{sha256}.svg` | Authorized hash-checked SVG |
| GET | `/api/runs/{id}/graphics/{sha256}.png` | Authorized hash-checked PNG |

Example body (use a **new** random request ID for each experiment):

```json
{
  "request_id": "0123456789abcdef0123456789abcdef",
  "family": "quantum",
  "prompt": "Build and verify Bell, simulate, then read the report.",
  "limits": {"max_steps": 5, "max_tools": 5, "seconds": 300},
  "reports": 0
}
```

Prompt length 1–8000, nonblank; family `quantum` or `qec`. Report goal 0–30,
Quantum only 0. Unknown fields are forbidden. POST bodies over 40000 bytes return
413. Unknown runs/unauthorized graphics return 404; corrupt graphics return 409.
Repeated identical ID/payload returns the existing run; changed or legacy
unverifiable payload returns 409. Poll every second and resume from `seq`.
The API does not expose a cancel route. `fixture` is output metadata, not an
accepted run request field.

## Python interfaces

`QuantumAdapter(root).execute(name, arguments, deadline)` uses a monotonic
deadline and no provider. `Agent`, `Limits`, `Finalization`, `Trace`, and `replay`
live in [runtime.py](../src/quantum_lab_agent/runtime.py). `Agent(...,
on_report=callback)` can deliver a report before optional interpretation.
These internal Python interfaces are not promised stable across pre-1.0 versions.
