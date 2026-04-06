# Project Structure

## Top-Level Layout

```text
.
├── README.md
├── docs/
├── manage.py
├── pyproject.toml
├── src/
│   ├── app.py
│   ├── app_factory.py
│   ├── config/
│   ├── management/
│   ├── modules/
│   └── dnk_app.py
└── test/
```

## Top-Level Directories

- `src/`: application code, module boundaries, configuration and entrypoints.
- `src/modules/`: business modules and shared infrastructure.
- `src/config/`: environment-backed settings groups and computed config.
- `src/management/`: management CLI parser and command handlers.
- `test/`: unit and integration-style tests around module behavior and architecture boundaries.
- `docs/`: project documentation.

## Modules Layout

```text
src/modules/
├── tenancy/
├── identity/
├── crm/
├── schema_registry/
└── shared/
```

## Common Module Shape

- `domain/`: entities, value objects, repository protocols, domain errors.
- `application/`: use cases, DTOs, commands, queries, application services.
- `infrastructure/`: persistence, adapters and integrations.
- `presentation/`: HTTP routers and dependency assembly.

`schema_registry` also has:

- `application/migration/`: physical PostgreSQL planning model and canonicalization.
- `seed/`: default and test seed modules used by create/diff flows.

## Management Layout

- `src/management/cli.py`: parser and command dispatch.
- `src/management/commands/`: concrete command namespaces.

## Related

- [Architecture overview](overview.md)
- [Modules](../modules/tenancy.md)
- [Management CLI](../interfaces/management-cli.md)

## Source Of Truth

- `src/modules/`
- `src/management/`
- `test/`
