# Security

## Scope

0.1.0 is a local research workbench, not an authenticated multi-user service.
Bind to loopback, use one worker and one instance per data root, and trust the
local operator/artifact directory. There is no advertised supported-release
maintenance window yet.

## Reporting

Use GitHub's enabled [private vulnerability reporting channel](https://github.com/JiuYang0u0/quantum-lab-agent/security/advisories/new).
Do not post credentials, personal data, private traces, or sensitive exploit details
in public issues. Remove secrets from attachments even when reporting privately.

If a key is exposed, revoke/rotate it with its provider. Redaction is best-effort,
not a guarantee that arbitrary prompts or reports are safe to publish. Do not
attach `.env`, raw databases, or entire `.qla` directories to reports.

The runtime restricts tools and validates artifacts, but timeouts do not cancel
external B jobs or force-stop already running CPU work. See
[limitations](docs/limitations.md) and [architecture](docs/architecture.md).
