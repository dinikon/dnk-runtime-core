# Management CLI

## Entry Point

The project exposes one Python script entry point:

- `dnk-manage = "management.cli:main"`

Parser bootstrap happens in `src/management/cli.py`.

## Current Command Tree

```text
dnk-manage
├── schema-registry
│   └── diff [<tenant_id> | --all] [--seed-path ...]
├── events
│   └── publish-outbox [--limit ...] [--max-attempts ...]
├── jobs
│   ├── process-due [--limit ...] [--max-attempts ...] [--lock-ttl-seconds ...]
│   └── recover-stuck [--limit ...] [--max-attempts ...]
└── communication
    ├── process-queued --tenant-id <uuid> [--limit ...]
    ├── publish-queued --tenant-id <uuid> [--limit ...]
    ├── recover-stuck --tenant-id <uuid> [--older-than-seconds ...] [--limit ...]
    └── worker
```

## Current Supported Command

### `dnk-manage schema-registry diff`

Runs `DiffSchemaUseCase` for a tenant runtime schema.

Arguments:

- `tenant_id`: UUID of the tenant; mutually exclusive with `--all`
- `--all`: runs diff for every tenant without status filtering
- `--seed-path`: optional Python module path that exports `SCHEMA_SEED`

Default seed path:

- `src.modules.schema_registry.seed.schema_seed`

## Output

On success:

- for a single tenant, prints one summary line:
    - `OK tenant_id=... schema_name=... seed_path=... operations=... destructive=... non_destructive=...`
- for `--all`, prints one `OK ...` line per successful tenant and a final summary:
  - `SUMMARY tenants=... succeeded=... failed=... operations=... destructive=... non_destructive=... rolled_back=false`
- exits with code `0`

On expected `SchemaRegistryError`:

- for a single tenant, prints short error text to `stderr`
- for `--all`, prints `ERROR tenant_id=... error=...` per failed tenant, continues the remaining tenants, rolls back the
  whole batch and prints:
  - `SUMMARY tenants=... succeeded=... failed=... operations=... destructive=... non_destructive=... rolled_back=true`
- exits with code `2`

Unexpected exceptions are not swallowed, so traceback remains visible for debugging.

### `dnk-manage communication process-queued`

Claims and processes queued outbound communication messages for one tenant without RabbitMQ.

Arguments:

- `--tenant-id`: UUID of the tenant
- `--limit`: maximum queued messages to process, defaults to `100`

On expected `CommunicationError`, prints the error to `stderr` and exits with code `2`.

### `dnk-manage events publish-outbox`

Publishes due shared integration events from PostgreSQL outbox to RabbitMQ.
Communication delivery status facts such as `communication.outbound_message.sent.v1`,
`communication.outbound_message.failed.v1`, `communication.outbound_message.delivered.v1` and
`communication.delivery_status.changed.v1` use this path after they are written to the shared outbox.

Arguments:

- `--limit`: maximum due outbox events to publish, defaults to `EVENT_BUS.publish_limit`
- `--max-attempts`: maximum publish attempts before an event is marked `failed`, defaults to `EVENT_BUS.max_attempts`

On success prints:

- `OK scanned=... published=... failed=...`

### `dnk-manage jobs process-due`

Claims due shared scheduled jobs from PostgreSQL and dispatches them by `job_type`.

Arguments:

- `--limit`: maximum due jobs to claim, defaults to `SCHEDULED_JOBS.process_limit`
- `--max-attempts`: maximum attempts before a job is marked `failed`, defaults to `SCHEDULED_JOBS.max_attempts`
- `--lock-ttl-seconds`: worker lock TTL for claimed jobs, defaults to `SCHEDULED_JOBS.lock_ttl_seconds`

On success prints:

- `OK scanned=... processed=... done=... failed=... retried=...`

### `dnk-manage jobs recover-stuck`

Recovers `running` scheduled jobs whose lock expired.

Arguments:

- `--limit`: maximum stuck jobs to inspect, defaults to `SCHEDULED_JOBS.recover_limit`
- `--max-attempts`: maximum attempts before a stuck job is marked `failed`, defaults to `SCHEDULED_JOBS.max_attempts`

On success prints:

- `OK scanned=... recovered=... failed=...`

### `dnk-manage communication publish-queued`

Publishes queued outbound communication messages to RabbitMQ for worker processing.
This is an operational delivery queue path, separate from `events publish-outbox`.

Arguments:

- `--tenant-id`: UUID of the tenant
- `--limit`: maximum queued messages to publish, defaults to `100`

### `dnk-manage communication recover-stuck`

Marks expired `SENDING` outbound messages as failed/unknown so they can be inspected or retried manually.

Arguments:

- `--tenant-id`: UUID of the tenant
- `--older-than-seconds`: stuck threshold, defaults to `300`
- `--limit`: maximum messages to recover, defaults to `100`

### `dnk-manage communication worker`

Runs the FastStream RabbitMQ communication worker. The worker parses outbound jobs, claims one outbound message with a
processing lease, sends it through the configured provider sender and persists the result in short transactions.

## Transaction Model

- CLI handler opens one `UnitOfWork`
- management builder assembles use case from the active `uow.session`
- commit/rollback is managed by `UnitOfWork.__aexit__`
- `events publish-outbox` publishes already-committed outbox rows and stores publish status in a new `UnitOfWork`
- `jobs process-due` and `jobs recover-stuck` use one `UnitOfWork` and compose shared jobs use cases through
  `shared.presentation.jobs`
- `schema-registry diff --all` uses one outer `UnitOfWork` and per-tenant savepoints; any expected tenant failure rolls
  back the whole outer transaction after all tenants are attempted
- communication worker-by-id opens short `UnitOfWork` scopes around claim/build and result persistence

## Related

- [Schema Registry module](../modules/schema-registry.md)
- [Shared module](../modules/shared.md)
- [Communication module](../modules/communication.md)
- [Request lifecycle](../architecture/request-lifecycle.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)

## Source Of Truth

- `src/management/cli.py`
- `src/management/commands/events.py`
- `src/management/commands/jobs.py`
- `src/management/commands/schema_registry.py`
- `src/modules/schema_registry/presentation/depends/management.py`
