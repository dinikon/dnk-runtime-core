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
└── jobs
│   ├── process-due [--limit ...] [--max-attempts ...] [--lock-ttl-seconds ...]
│   └── recover-stuck [--limit ...] [--max-attempts ...]
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

### `dnk-manage events publish-outbox`

Publishes due shared integration events from PostgreSQL outbox to RabbitMQ.

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

## Transaction Model

- CLI handler opens one `UnitOfWork`
- management builder assembles use case from the active `uow.session`
- commit/rollback is managed by `UnitOfWork.__aexit__`
- `events publish-outbox` publishes already-committed outbox rows and stores publish status in a new `UnitOfWork`
- `jobs process-due` and `jobs recover-stuck` use one `UnitOfWork` and compose shared jobs use cases through
  `shared.presentation.jobs`
- `schema-registry diff --all` uses one outer `UnitOfWork` and per-tenant savepoints; any expected tenant failure rolls
  back the whole outer transaction after all tenants are attempted

## Related

- [Schema Registry module](../modules/schema-registry.md)
- [Shared module](../modules/shared.md)
- [Request lifecycle](../architecture/request-lifecycle.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)

## Source Of Truth

- `src/management/cli.py`
- `src/management/commands/events.py`
- `src/management/commands/jobs.py`
- `src/management/commands/schema_registry.py`
- `src/modules/schema_registry/presentation/depends/management.py`
