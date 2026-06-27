Security
========

Status: initial security guidance

Purpose
-------

This document records the security assumptions and requirements for Docker
Health Alert Monitor.

Docker Socket Access
--------------------

The service requires access to the Docker Engine API through `/var/run/docker.sock`
or `DOCKER_HOST`.

Mounting the Docker socket is privileged, even when mounted read-only:

```text
/var/run/docker.sock:/var/run/docker.sock:ro
```

Docker socket access can expose sensitive container metadata, environment
details, labels, image names, mounts, network settings, and healthcheck output.
Depending on daemon configuration, Docker API access may also allow operations
that affect the host. Run this service only where it is trusted.

Secret Inputs
-------------

Prefer file-based secret inputs over inline configuration.

Preferred:

```yaml
config:
  webhook_url_file: /run/secrets/discord_webhook
```

Avoid when possible:

```yaml
config:
  webhook_url: https://discord.com/api/webhooks/example
```

Secret file values must not be logged. The service should strip one trailing
newline from file-loaded secrets for compatibility with Docker secrets and
similar secret mounts.

Values Treated As Secrets
-------------------------

These values are always sensitive:

- Webhook URLs.
- API tokens.
- Authorization headers.
- Cookie headers.
- Basic auth credentials.
- Header values loaded from files.
- Secret file contents.

Logs and delivery results must not include these values.

Logging Redaction
-----------------

The service logs structured JSON to stdout. Logs should include operational
context but must avoid leaking secrets.

Safe log fields:

- Receiver name.
- Plugin name.
- Alert status.
- Container ID.
- Container name.
- Attempt number.
- Delivery result status.
- Safe error class or summary.

Unsafe log fields:

- Webhook URL.
- Authorization header.
- Token value.
- Secret file contents.
- Full request headers.
- Raw provider request body when it may include secrets.

When a secret value needs to be represented, use a redacted marker such as
`[redacted]`.

Label Redaction
---------------

Container labels can contain credentials or operational secrets. The normalized
alert object must redact sensitive labels by default before alerts are routed to
plugins.

Sensitive label key matching should be case-insensitive and should include keys
containing:

- `password`
- `passwd`
- `secret`
- `token`
- `key`
- `credential`
- `authorization`
- `auth`

Example:

```json
{
  "com.example.owner": "media",
  "com.example.api_token": "[redacted]"
}
```

Healthcheck Output
------------------

Docker healthcheck output can contain URLs, command output, stack traces, or
other sensitive data. The service must truncate healthcheck output according to
configuration before including it in normalized alerts.

Default maximum output length:

```yaml
monitor:
  health_log_output_limit: 1000
```

Future implementations may add pattern-based redaction for healthcheck output,
but truncation is required from the first implementation.

Receiver Isolation
------------------

Receiver plugin failures should not crash the core event loop unless a receiver
or route is explicitly configured as fatal.

This prevents a compromised or broken destination from stopping Docker health
observation for other receivers.

Provider-Specific Dependencies
------------------------------

Provider-specific dependencies must not be loaded unless the corresponding
plugin is configured.

This reduces runtime attack surface and avoids initializing unused integrations
with accidental credentials or environment variables.

Configuration Files
-------------------

Configuration files may contain non-secret operational metadata, but can still
contain sensitive inline values if operators choose inline secrets. Operators
should mount configuration files read-only and restrict filesystem permissions.

Recommended mounts:

```text
./config:/config:ro
./secrets:/run/secrets:ro
```

The example files under `examples/secrets/` contain non-secret example values
only.
Production deployments should mount real secrets from a protected secret store
or host path with restricted permissions.

Least Privilege
---------------

The container image should run as a non-root user when possible. The effective
user must still be able to access the Docker socket or configured `DOCKER_HOST`.

The service does not need:

- Host network mode by default.
- Privileged container mode.
- Write access to the Docker socket mount.
- Write access to configuration or secret mounts.

Security Review Checklist
-------------------------

Before release, verify:

- Webhook URLs are redacted from logs.
- Authorization headers are redacted from logs.
- Secret file contents are never logged.
- Sensitive labels are redacted in normalized alerts.
- Healthcheck output is truncated.
- Missing secret files fail startup clearly.
- Unconfigured plugins are not imported.
- Docker socket risk is documented in deployment examples.
