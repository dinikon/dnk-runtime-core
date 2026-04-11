# Management CLI

## Entry Point

The project exposes one Python script entry point:

- `dnk-manage = "management.cli:main"`

Parser bootstrap happens in `src/management/cli.py`.

## Current Command Tree

```text
dnk-manage
└── schema-registry
    └── diff <tenant_id> [--seed-path ...]
```

## Current Supported Command

### `dnk-manage schema-registry diff`

Runs `DiffSchemaUseCase` for a tenant runtime schema.

Arguments:

- `tenant_id`: UUID of the tenant
- `--seed-path`: optional Python module path that exports `SCHEMA_SEED`

Default seed path:

- `src.modules.schema_registry.seed.schema_seed`

## Output

On success:

- prints one summary line:
    - `OK tenant_id=... schema_name=... seed_path=... operations=... destructive=... non_destructive=...`
- exits with code `0`

On expected `SchemaRegistryError`:

- prints short error text to `stderr`
- exits with code `2`

Unexpected exceptions are not swallowed, so traceback remains visible for debugging.

## Transaction Model

- CLI handler opens one `UnitOfWork`
- management builder assembles use case from the active `uow.session`
- commit/rollback is managed by `UnitOfWork.__aexit__`

## Related

- [Schema Registry module](../modules/schema-registry.md)
- [Request lifecycle](../architecture/request-lifecycle.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)

## Source Of Truth

- `src/management/cli.py`
- `src/management/commands/schema_registry.py`
- `src/modules/schema_registry/presentation/depends/management.py`
