Plugin Contract
===============

Status: initial plugin contract

Purpose
-------

Receiver plugins deliver normalized alerts to external systems. Plugins are the
only place where provider-specific formatting and delivery behavior should live.
The core event engine must remain provider-neutral.

Plugin Identity
---------------

Each plugin has a stable configured name.

Initial names:

- `generic-webhook`
- `discord`

Built-in configured names are mapped to import paths by the plugin registry.
External plugins may also be referenced by dotted Python module path, such as
`e2e_plugins.drop_receiver`, when that module is available on `PYTHONPATH`.
A plugin module must only be imported when at least one configured receiver
references that plugin.

Receiver Instance
-----------------

A receiver is a named plugin instance:

```yaml
receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: /run/secrets/discord_webhook
```

The same plugin can be used by multiple receiver instances with different
configuration.

Plugin Interface
----------------

The implementation language may evolve, but the first Python interface should
look conceptually like this:

```python
class ReceiverPlugin(Protocol):
    name: str

    def validate_config(self, config: Mapping[str, object]) -> None:
        ...

    def create_receiver(
        self,
        name: str,
        config: Mapping[str, object],
    ) -> "Receiver":
        ...


class Receiver(Protocol):
    name: str

    async def deliver(self, alert: Mapping[str, object]) -> "DeliveryResult":
        ...
```

`validate_config` should detect missing required settings, invalid durations,
and unreadable configured secret files before live event processing starts.

Delivery Result
---------------

Plugins must return a structured delivery result.

```json
{
  "status": "success",
  "message": "delivered",
  "retry_after_seconds": null
}
```

Valid statuses:

- `success`: Delivery completed.
- `retryable_failure`: Delivery failed and may succeed when retried.
- `permanent_failure`: Delivery failed and should not be retried.

Fields:

- `status`: Required delivery status.
- `message`: Optional safe summary. Must not contain secrets.
- `retry_after_seconds`: Optional plugin-provided retry delay hint.

Retry Semantics
---------------

The delivery coordinator owns retry loops. Plugins classify failures but should
not perform their own outer retry loop unless the behavior is provider-specific
and documented.

Retryable examples:

- Network timeout.
- DNS failure.
- Connection reset.
- HTTP 429.
- HTTP 500 through 599.
- Generic webhook non-2xx responses unless configured otherwise.

Permanent examples:

- Invalid receiver configuration.
- Missing required secret file at startup.
- Payload cannot be serialized.
- Provider response that clearly indicates the destination does not exist.

Plugin failures must not crash the core event loop unless the receiver or route
is configured as fatal.

Alert Input
-----------

Plugins receive only the normalized alert object, not Docker SDK container
objects or raw Docker events.

The alert object has this shape:

```json
{
  "version": "1",
  "status": "firing",
  "alert": "DockerContainerUnhealthy",
  "host": "serenity",
  "severity": "warning",
  "container": {
    "id": "abc123",
    "name": "qbittorrent",
    "image": "lscr.io/linuxserver/qbittorrent:latest",
    "state": "running",
    "health": "unhealthy",
    "previous_health": "healthy"
  },
  "compose": {
    "project": "gt",
    "service": "qbittorrent"
  },
  "labels": {},
  "event": {
    "source": "docker",
    "time": "2026-06-27T17:00:00Z"
  },
  "health_log": {
    "exit_code": 1,
    "output": "truncated healthcheck output"
  }
}
```

Plugins may ignore fields they do not need.

Plugin Responsibilities
-----------------------

Plugins may:

- Validate plugin-specific configuration.
- Load plugin-specific secrets from configured files.
- Format provider-specific payloads.
- Send alerts to provider APIs or webhooks.
- Return structured delivery results.
- Provide safe log context.

Plugins must not:

- Connect to Docker.
- Subscribe to Docker events.
- Inspect raw Docker SDK objects.
- Apply monitor filters.
- Suppress duplicate health states.
- Mutate core state.
- Decide global routing.
- Log secret values.

Secret Handling
---------------

Plugins must prefer file-based secrets over inline values when both are
available.

Secret examples:

- Webhook URLs.
- Authorization headers.
- API tokens.
- Basic auth passwords.
- Header values loaded from files.

Plugins must not include secrets in:

- Exceptions.
- Delivery result messages.
- Log fields.
- Debug output.
- Test snapshots.

Provider URLs should be represented in logs as a redacted marker, for
example `[redacted-webhook-url]`.

Generic Webhook Plugin Contract
-------------------------------

The `generic-webhook` plugin sends HTTP POST requests.

Input config:

```yaml
config:
  url_file: /run/secrets/webhook_url
  timeout: 10s
  retries: 3
  headers:
    X-Source: docker-monitor
  header_files:
    Authorization: /run/secrets/webhook_authorization
```

Behavior:

- Read `url_file` if configured, otherwise use `url`.
- Send the normalized alert object as JSON by default.
- Support `payload_template` with `{field.path}` tokens for JSON payload
  shaping.
- Apply static headers and file-loaded headers.
- Treat network exceptions as `retryable_failure`.
- Treat non-2xx responses as `retryable_failure` by default.
- Return `success` for 2xx responses.
- Redact URLs and secret headers in logs and errors.

Discord Plugin Contract
-----------------------

The `discord` plugin sends Discord webhook messages.

Input config:

```yaml
config:
  webhook_url_file: /run/secrets/discord_webhook
  timeout: 10s
  retries: 3
```

Behavior:

- Read `webhook_url_file` if configured, otherwise use `webhook_url`.
- Convert `firing` alerts into an unhealthy container message.
- Convert `resolved` alerts into a recovery message.
- Convert `starting` alerts only when the core service emits them.
- Include container name, image, host, Compose project/service, health state,
  and truncated health log output when available.
- Return `success` for Discord 2xx responses.
- Classify network failures, Discord 429, and Discord 5xx responses as
  retryable.
- Classify other Discord 4xx responses as permanent failures.
- Redact the webhook URL in logs and errors.

Adding A New Plugin
-------------------

To add a future receiver:

1. Create a module under the receiver plugin namespace.
2. Implement the receiver plugin interface.
3. Reference the plugin by dotted module path, or add a short built-in alias and
   import path to the plugin registry.
4. Add plugin-specific configuration validation.
5. Add tests for config validation, payload formatting, delivery
   classification, and secret redaction.
6. Document the plugin configuration.

Adding a receiver plugin must not require changes to Docker event
reconciliation, monitor filtering, state tracking, or alert normalization.
