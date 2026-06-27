# Docker Compose Example

This directory contains a runnable example for the containerized service.

Validate the example Compose file:

```sh
docker compose -f examples/compose.yaml config
```

Build and run the image locally:

```sh
docker build --target runtime -t docker-monitor:local .
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v "$PWD/examples/config.yaml:/config/config.yaml:ro" \
  -v "$PWD/examples/secrets:/run/secrets:ro" \
  docker-monitor:local healthcheck
```

The sample secret files contain non-secret example URLs. Replace them with
real secret mounts in production.
