Architecture
============

Status: initial architecture

Purpose
-------

This document describes the service boundaries and runtime flow for Docker
Health Alert Monitor. The goal is to keep Docker event handling, alert state,
routing, and provider-specific delivery cleanly separated.

System Overview
---------------

The service has four main layers:

```text
Docker Engine
  -> Docker source adapter
  -> Core event engine
  -> Router and delivery coordinator
  -> Receiver plugins
```

The Docker source adapter is the only layer that talks directly to Docker. The
core event engine owns filtering, reconciliation, normalization, and state
transitions. The router decides which configured receivers should receive an
alert. Receiver plugins handle provider-specific payloads and delivery.

Core Modules
------------

Recommended module responsibilities:

- `config`: Load and validate YAML configuration.
- `docker_source`: Connect to Docker, list containers, inspect health state, and
  stream Docker health events.
- `filters`: Decide whether a container is monitored.
- `state`: Track previous health by container ID and suppress unchanged states.
- `alerts`: Build provider-neutral alert objects.
- `routing`: Match alerts to configured receivers.
- `plugins`: Load configured receiver plugins and define delivery result types.
- `engine`: Coordinate startup reconciliation, live event handling, retries,
  shutdown, and reconnects.
- `logging`: Emit structured JSON logs with secret redaction.

Receiver plugins should live outside these core modules, for example under
`receivers/`.

Startup Flow
------------

Startup should happen in this order:

1. Install signal handlers for `SIGTERM` and `SIGINT`.
2. Load configuration from the configured YAML file.
3. Validate configuration and route references.
4. Load only the receiver plugins referenced by configured receivers.
5. Initialize configured receiver instances.
6. Connect to Docker through `/var/run/docker.sock` or `DOCKER_HOST`.
7. Inspect existing containers.
8. Reconcile current container health state.
9. Start the live Docker event stream.

If configuration validation fails, startup must fail with a clear error before
the service starts consuming Docker events.

Startup Reconciliation Flow
---------------------------

For each existing container:

1. Ignore containers without a Docker healthcheck.
2. Apply monitor filters.
3. Read current health state.
4. Record current state by container ID.
5. Emit a startup `firing` alert if the current health is `unhealthy`.
6. Emit a startup `starting` alert only when `send_starting` is enabled.
7. Do not alert for healthy containers unless a future config option explicitly
   enables that behavior.

This prevents already unhealthy containers from being missed when the service
starts after the failure.

Live Event Flow
---------------

The service subscribes to Docker events with these filters:

```text
type=container
event=health_status
```

For each live health event:

1. Extract the container ID and reported health status.
2. Inspect or retrieve container metadata needed for filtering and alert
   normalization.
3. Ignore containers without healthchecks.
4. Apply monitor filters.
5. Ask the state tracker whether the health value changed.
6. Suppress the event if the health value is unchanged.
7. Convert the health transition into an alert status:
   - `unhealthy` -> `firing`
   - `healthy` -> `resolved` when `send_resolved` is enabled
   - `starting` -> `starting` when `send_starting` is enabled
8. Build the normalized alert object.
9. Route the alert to matching receivers.
10. Deliver through receiver plugins with retry handling.

State Model
-----------

The state tracker stores the last observed health state by full Docker container
ID.

State must be keyed by container ID rather than name because names can be reused
and Compose recreates containers during deployments. If a container disappears,
its state can be removed when Docker emits a destroy/remove event or during a
future periodic cleanup pass. The initial implementation can tolerate stale
state for stopped containers because a recreated container receives a new ID.

Duplicate Suppression
---------------------

The event engine should emit alerts only when health state changes. For example:

```text
unknown -> unhealthy  => firing
unhealthy -> unhealthy => suppress
unhealthy -> healthy  => resolved
healthy -> healthy    => suppress
healthy -> starting   => starting if enabled, otherwise record and suppress
```

If `send_resolved` is disabled, the transition to healthy should still update
state even though no alert is delivered.

Alert Normalization Boundary
----------------------------

The alert normalizer converts Docker-specific container data into a stable
provider-neutral object. Receiver plugins must not inspect raw Docker SDK
objects.

The normalized alert object is the contract between core and plugins. It should
contain enough information for provider formatting without requiring provider
plugins to know Docker internals.

Routing Boundary
----------------

Routes match normalized alert fields, not raw Docker event fields.

Initial routing uses exact matches. A route can deliver to one or more receiver
names. If no route matches, the alert is logged and dropped without error.

Plugin Boundary
---------------

Plugins receive:

- The normalized alert object.
- The plugin-specific receiver configuration.
- A logger or context that already redacts configured secrets.

Plugins return:

- `success`
- `retryable_failure`
- `permanent_failure`

Plugins must not:

- Subscribe to Docker events.
- Perform monitor filtering.
- Mutate core state.
- Decide whether a duplicate health state should be suppressed.
- Log webhook URLs or secret values.

Reconnect Behavior
------------------

Docker event streams can disconnect during daemon restarts, network failures, or
socket interruptions. The engine should treat stream termination as retryable
unless shutdown has been requested.

Recommended reconnect behavior:

- Log the disconnect reason with a safe error message.
- Wait with bounded backoff.
- Reconnect to Docker.
- Reconcile current state again before resuming events.

Reconciliation after reconnect ensures missed events do not leave the service
with stale health state.

Graceful Shutdown
-----------------

On `SIGTERM` or `SIGINT`, the service should:

1. Mark shutdown requested.
2. Stop reading new Docker events.
3. Allow in-flight deliveries to finish within a bounded grace period.
4. Cancel pending retries after the grace period.
5. Flush logs.
6. Exit with status code `0` for normal shutdown.

Failure Isolation
-----------------

Receiver failures must not crash the Docker event loop unless the receiver or
route is explicitly configured as fatal.

A failed receiver delivery should produce structured logs including receiver
name, delivery status, attempt number, and a safe error summary. Other matching
receivers should still be attempted.
