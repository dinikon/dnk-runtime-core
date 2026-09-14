# Runtime–Control Plane integration

The `control_plane` module owns Runtime's protocol v1 boundary. Core assigns placement, DNS and cloud configuration; Runtime owns tenant schemas, users, access and sessions. No shared database or broker is required between services.

## Durable installation

The global registry maps Core UUID to a reserved Runtime UUID and unique hostname. Attempts retain operation ID, command digest, encrypted replay snapshot, state, observed resources, current step and expiring fencing token. Fernet protects the snapshot and reusable client secret. Backup recovery requires both database and encryption key.

Acceptance serializes tenant/attempt identities, checks the permanent resource registry and commits an outbox wakeup before `202`. Duplicate commands return the original result; changed commands conflict. Another attempt requires saved failure and verified absence. Worker recovery never infers resource absence from a missing attempt.

The installer uses tenancy's existing transaction for schema, tenant migrations, Owner and cloud identity bootstrap. The preallocated Runtime UUID makes resource reconciliation deterministic. Checkpoints require the current attempt, fencing token and an unexpired lease. Lost broker messages or replies can be retried; PostgreSQL determines whether work is complete. Unknown resources are retained for reconciliation; no automatic user-data deletion occurs.

## Access projection

Identity invokes a transaction-bound port when cloud access changes. Local rights, the persistent monotonically increasing version and the outbox event commit together. Versions survive unlink/relink. The initial Owner event has version 1.

RabbitMQ messages carry UUIDs only. A wakeup is acknowledged at broker publication; an access event is delivered only after Core returns a valid `200`, including `applied=false`. Temporary failures retry with backoff. Identity/contract errors block hot retries and remain visible. Core downtime does not undo local changes.

## Background services and readiness

`python -m src.modules.control_plane.worker` runs the dedicated RabbitMQ consumer, dispatcher, reconciliation, heartbeat and zone-observation loops. Credentials/vhost and installation/access queues are independent of the general event bus. `--healthcheck` checks the current application/schema generation's worker heartbeat.

Zone probes connect to the configured public ingress address with `dnk-probe-<instance UUID without hyphens>.<zone>` as SNI/Host. They verify TLS and this Instance's response without requiring a Tenant DNS record. Routing/TLS observations are stored separately; stale observations are not ready.

Public Tenant readiness checks successful installation, local schema, decryptable cloud configuration and a fresh healthy worker heartbeat without requesting Core tokens. The heartbeat verifies the local Redis auth store and RabbitMQ. Later local access changes do not reinstall resources. Core performs a real DNS/HTTPS probe before activation.

## Structure

Application ports and use cases define protocol/orchestration; infrastructure supplies SQLAlchemy persistence, encryption, tenancy/identity adapters, delivery and observations; presentation composes the current UoW and exposes HTTP. Shared infrastructure supplies generic RabbitMQ transport, migrations and process metrics.

## Tests

`test_control_plane_runtime.py` covers real PostgreSQL acceptance, concurrency, fencing, installation recovery and delivery. `test_management_trust_boundary.py` covers peer/certificate trust; `test_global_migrations_postgres.py` covers fresh installation and refusal to overwrite an existing unversioned database. Helm tests check management isolation, zones, secrets and workers. Live ingress checks are separate from manifest rendering.

See [tenant deletion](tenant-deletion.md), [HTTP API](../interfaces/http-api.md), [contract schemas](../contracts/runtime-v1/README.md), [Tenancy](tenancy.md), [Identity](identity.md), [release checks](../deployment/control-plane-v1.md) and [Helm](../../helm/README.md).
