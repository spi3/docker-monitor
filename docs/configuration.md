Configuration Reference
=======================

Status: initial configuration reference

Purpose
-------

The service is configured primarily through a YAML file. File-based
configuration keeps receiver setup readable, supports GitOps workflows, and
avoids a large collection of environment variables.

Config File Location
--------------------

Recommended container default:

```text
/config/config.yaml
```

The service should support an environment variable for the config path:

```text
CONFIG_FILE=/config/config.yaml
```

Validate a configuration file with:

```sh
uv run docker-health-alerts config-check --config /config/config.yaml
```

If `--config` is omitted, the command reads `CONFIG_FILE` and then falls back to
`/config/config.yaml`.

Top-Level Schema
----------------

```yaml
host: serenity
severity: warning

monitor:
  mode: label_opt_in
  label: docker-health-alert.enable
  send_resolved: true
  send_starting: false
  health_log_output_limit: 1000
  filters: {}

receivers: []

routes: []
```

Top-level fields:

- `host`: Optional host name included in alerts. Defaults to the runtime
  hostname.
- `severity`: Optional default alert severity. Defaults to `warning`.
- `monitor`: Monitor filtering and alert emission settings.
- `receivers`: Named receiver plugin instances.
- `routes`: Alert routing rules.

Monitor Configuration
---------------------

```yaml
monitor:
  mode: label_opt_in
  label: docker-health-alert.enable
  send_resolved: true
  send_starting: false
  health_log_output_limit: 1000
```

Fields:

- `mode`: `label_opt_in` or `label_opt_out`. Defaults to `label_opt_in`.
- `label`: Docker label used by the selected monitor mode. Defaults to
  `docker-health-alert.enable`.
- `send_resolved`: Emit `resolved` alerts when unhealthy containers become
  healthy. Defaults to `true`.
- `send_starting`: Emit `starting` alerts. Defaults to `false`.
- `health_log_output_limit`: Maximum healthcheck output characters included in
  alerts. Defaults to `1000`.

Monitor Modes
-------------

In `label_opt_in` mode, only containers with the configured label set to `true`
are monitored.

```yaml
labels:
  docker-health-alert.enable: "true"
```

In `label_opt_out` mode, all containers are monitored except containers with the
configured label set to `false`.

```yaml
labels:
  docker-health-alert.enable: "false"
```

Label boolean comparisons should be case-insensitive and should trim surrounding
whitespace.

Optional Filters
----------------

Optional filters further restrict monitored containers after the monitor mode is
applied.

```yaml
monitor:
  filters:
    names:
      - qbittorrent
      - sonarr
    images:
      - lscr.io/linuxserver/qbittorrent
    compose_projects:
      - gt
    compose_services:
      - qbittorrent
    labels:
      com.example.tier: media
      com.example.alerts: enabled
```

Filter behavior:

- Empty or omitted filters match all containers allowed by the monitor mode.
- `names` match normalized container names without a leading slash.
- `images` should match either exact image references or repository prefixes.
- `compose_projects` match `com.docker.compose.project`.
- `compose_services` match `com.docker.compose.service`.
- `labels` require each configured label key and value to match.

Receivers
---------

Receivers are named plugin instances.

```yaml
receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: /run/secrets/discord_webhook

  - name: raw-webhook
    plugin: generic-webhook
    config:
      url: https://example.internal/docker-alerts
      timeout: 10s
      retries: 3
```

Receiver fields:

- `name`: Unique receiver name referenced by routes.
- `plugin`: Plugin identifier, such as `discord` or `generic-webhook`.
- `config`: Plugin-specific configuration object.
- `fatal`: Optional boolean. If true, final delivery failure may stop the
  service. Defaults to `false`.

Routes
------

Routes match normalized alert fields and list receivers to notify.

```yaml
routes:
  - match:
      severity: warning
    receivers:
      - discord-lab
      - raw-webhook
```

Initial route matching is exact-match only. Supported first-pass match keys:

- `status`
- `alert`
- `severity`
- `host`
- `container.name`
- `container.image`
- `container.health`
- `compose.project`
- `compose.service`

If no route matches an alert, the service logs a `route.unmatched` event and
drops the alert.

Generic Webhook Configuration
-----------------------------

```yaml
receivers:
  - name: raw-webhook
    plugin: generic-webhook
    config:
      url_file: /run/secrets/webhook_url
      timeout: 10s
      retries: 3
      headers:
        X-Source: docker-health-alert
      header_files:
        Authorization: /run/secrets/webhook_authorization
```

Fields:

- `url`: Inline webhook URL.
- `url_file`: File containing the webhook URL.
- `timeout`: Request timeout. Defaults to `10s`.
- `retries`: Retry count for retryable failures. Defaults to `3`.
- `headers`: Static HTTP headers.
- `header_files`: HTTP header values loaded from files.
- `payload_template`: Optional JSON template for advanced payload shaping.

`url_file` is preferred over `url`. Header values loaded from files are
secrets and must not be logged.

The generic webhook plugin sends the normalized alert object as JSON when
`payload_template` is not configured.

Discord Configuration
---------------------

```yaml
receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: /run/secrets/discord_webhook
      timeout: 10s
      retries: 3
```

Fields:

- `webhook_url`: Inline Discord webhook URL.
- `webhook_url_file`: File containing the Discord webhook URL.
- `timeout`: Request timeout. Defaults to `10s`.
- `retries`: Retry count for retryable failures. Defaults to `3`.

`webhook_url_file` is preferred over `webhook_url`.

Secret File Handling
--------------------

Secret file values should be read during receiver initialization. Values should
be stripped of one trailing newline to support Docker secrets and Kubernetes
secret mounts.

Secret file paths should be validated when the receiver initializes. Missing or
unreadable configured secret files should fail startup with a clear error.

Validation Rules
----------------

Startup validation must reject configuration when:

- A receiver is missing `name` or `plugin`.
- Receiver names are duplicated.
- A route references an unknown receiver.
- `monitor.mode` is not `label_opt_in` or `label_opt_out`.
- A duration value cannot be parsed.
- A plugin referenced by a receiver is unknown.
- A required plugin secret is missing.
- Both inline and file variants are provided where a plugin disallows ambiguity.

Example: Label Opt-In With Discord
----------------------------------

```yaml
host: serenity

monitor:
  mode: label_opt_in
  label: docker-health-alert.enable
  send_resolved: true
  send_starting: false

receivers:
  - name: discord-lab
    plugin: discord
    config:
      webhook_url_file: /run/secrets/discord_webhook

routes:
  - match:
      severity: warning
    receivers:
      - discord-lab
```

Example: Label Opt-Out With Generic Webhook
-------------------------------------------

```yaml
host: serenity

monitor:
  mode: label_opt_out
  label: docker-health-alert.enable
  health_log_output_limit: 500

receivers:
  - name: raw-webhook
    plugin: generic-webhook
    config:
      url: https://example.internal/docker-alerts
      timeout: 5s
      retries: 2

routes:
  - match:
      status: firing
    receivers:
      - raw-webhook
```
