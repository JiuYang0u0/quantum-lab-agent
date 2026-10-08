# Security

## Scope

0.1.0 is a local research workbench, not an authenticated multi-user service.
Bind to loopback, use one worker and one instance per data root, and trust the
local operator/artifact directory. There is no advertised supported-release
maintenance window yet.

## Reporting

No private security reporting channel or email is configured for this local
repository. If an issue tracker is available, open only a minimal, non-sensitive
request asking maintainer JiuYang to establish a private channel. **Do not post
credentials, exploit payloads, personal data, private traces, or sensitive details
publicly.** Wait for a verified private contact before sharing those details.
For a local copy, contact the person who supplied it to arrange a private channel.

If a key is exposed, revoke/rotate it with its provider. Redaction is best-effort,
not a guarantee that arbitrary prompts or reports are safe to publish. Do not
attach `.env`, raw databases, or entire `.qla` directories to reports.

The runtime restricts tools and validates artifacts, but timeouts do not cancel
external B jobs or force-stop already running CPU work. See
[limitations](docs/limitations.md) and [architecture](docs/architecture.md).
