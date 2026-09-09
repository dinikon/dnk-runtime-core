# RabbitMQ dependency

Runs one RabbitMQ instance with the official `rabbitmq:3.13-management-alpine`
image. A ClusterIP Service exposes AMQP port 5672; the management UI is not
published. A headless Service provides the StatefulSet identity.

Set `auth.username`, `auth.vhost` and `auth.password.value` or
`auth.password.existingSecret.name/key`. There is no generated/default password.
Inline credentials become a Secret; the container receives them through
`secretKeyRef`, without passwords in its command arguments.

`persistence.enabled` retains `/var/lib/rabbitmq`, including the broker state and
Erlang cookie. `existingClaim` can reuse an existing writable PVC; otherwise the
StatefulSet creates a claim which survives uninstall. Preserve the release/name
overrides and credentials when reinstalling. Changing the Secret does not rotate
credentials in an initialized broker; perform that operation explicitly.

The Alpine image uses UID 100 and GID 101. A different image family may require
different pod security settings. Readiness/liveness use `rabbitmq-diagnostics`.
This package does not provide HA or TLS termination. Runtime can connect to an
external broker instead by setting `rabbitmq.enabled=false` in the application
chart and supplying external host/port/auth or a Secret-backed AMQP(S) URL.
