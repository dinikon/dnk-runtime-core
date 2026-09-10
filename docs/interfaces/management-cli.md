# Management CLI

## Entry Point

The project exposes one Python script entry point:

- `dnk-manage = "management.cli:main"`

Parser bootstrap happens in `src/management/cli.py`.

## Tenant migrations

```sh
dnk-manage tenant-migrations upgrade <tenant_id>
dnk-manage tenant-migrations upgrade --all
dnk-manage tenant-migrations current <tenant_id>
dnk-manage tenant-migrations current --all
dnk-manage tenant-migrations revision --autogenerate --tenant-id <tenant_id> -m "Describe the change"
```

`upgrade` and `current` require exactly one target: a tenant UUID or `--all`. Unknown tenants and absent schemas are errors. `current` reports `base` if no version exists and does not create version tables.

Each tenant runs in its own transaction. Batches continue after failures and preserve successful upgrades. Output contains per-tenant `OK` or `ERROR` lines and `tenants=... succeeded=... failed=...`. Exit status is 0 on success, 2 on command/target failure; invalid arguments also return 2.

`revision` uses one tenant at the current head to generate a draft through a separate reflection engine. Review the generated revision before applying it. See [tenant migrations](../data/tenant-migrations.md).

## Other commands

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
- `tenant-migrations upgrade --all` uses one UoW per tenant; failures do not roll back successful tenants.

## Related

- [Inventory module](../modules/inventory.md)
- [Shared module](../modules/shared.md)
- [Request lifecycle](../architecture/request-lifecycle.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)

## Source Of Truth

- `src/management/cli.py`
- `src/management/commands/events.py`
- `src/management/commands/jobs.py`
- `src/management/commands/tenant_migrations.py`
- `src/modules/tenancy/presentation/depends/management.py`
