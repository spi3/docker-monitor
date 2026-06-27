Docker Health Alert Monitor
===========================

Vision
------

Docker Health Alert Monitor is a small containerized service that watches
Docker container health transitions and sends alerts through modular receiver
plugins. It is meant to be simple to run beside existing Docker or Docker
Compose workloads, especially in GitOps-managed home lab and small operations
environments.

The service focuses on one job: observe Docker health state and deliver clear,
provider-neutral alerts. It does not restart containers, replace monitoring
systems, run a UI, or become a full incident management platform.

Core Idea
---------

Docker already has container healthchecks, but health transitions are easy to
miss unless another system consumes Docker events. This project closes that gap
by subscribing to Docker health events, reconciling current state at startup,
normalizing those transitions into a stable internal alert model, and routing
the result to configured receivers.

Receiver integrations such as Discord, Slack, ntfy, Gotify, SMTP, or generic
webhooks are intentionally outside the core event engine. The core service owns
Docker observation, state tracking, filtering, routing, retry orchestration, and
logging. Provider-specific formatting and delivery live in plugins that are
loaded only when referenced by configuration.

Design Principles
-----------------

- Keep Docker event handling provider-neutral.
- Make configuration file based and friendly to GitOps workflows.
- Use Docker labels as the primary opt-in or opt-out mechanism.
- Suppress duplicate alerts when a container's observed health state has not
  changed.
- Prefer explicit plugin loading so unused integrations and dependencies are
  not initialized.
- Treat delivery failures as isolated receiver failures unless configured to be
  fatal.
- Avoid leaking secrets in logs, including webhook URLs, auth headers, and file
  loaded secret values.
- Document Docker socket access as privileged, even when the socket is mounted
  read-only.

Primary Users
-------------

- Operators of Docker Compose stacks who want health alerts without installing a
  full monitoring stack.
- Homelab users who want simple Discord, webhook, or future ntfy/Gotify alerts.
- Small services that already use Docker healthchecks and need a lightweight
  alerting bridge.
- GitOps users who prefer labels and file-based configuration over manual state
  stored in a database.

High-Level Architecture
-----------------------

The service is split into four conceptual layers:

1. Docker source

   Connects to Docker through `/var/run/docker.sock` or `DOCKER_HOST`, inspects
   existing containers at startup, and subscribes to live container
   `health_status` events.

2. Core event engine

   Applies monitor filters, tracks previous health state by container ID,
   suppresses duplicates, converts Docker state into normalized alert objects,
   and emits `firing`, `resolved`, and optional `starting` alerts.

3. Router and delivery coordinator

   Matches normalized alerts against routes, invokes configured receivers,
   retries retryable failures, logs structured delivery results, and handles
   graceful shutdown.

4. Receiver plugins

   Implement provider-specific delivery. Plugins receive the normalized alert
   object plus plugin-specific config, and return structured results:
   `success`, `retryable_failure`, or `permanent_failure`.

Initial Receivers
-----------------

The first receiver plugins are:

- `generic-webhook`: Sends HTTP POST requests containing the normalized alert
  object by default, with optional JSON payload templating and custom headers.
- `discord`: Converts normalized alerts into Discord-friendly webhook messages.

Future receiver plugins should be possible without changing Docker event
handling code. Candidate future receivers include Slack, ntfy, Gotify,
Alertmanager webhook, SMTP, and Pushover.

Non-Goals
---------

- No web UI.
- No manual configuration database.
- No container restart or remediation behavior.
- No Prometheus rule engine replacement.
- No hard dependency on Discord, Slack, or any other provider.
- No provider-specific formatting in the Docker event engine.
