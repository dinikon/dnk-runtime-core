# Project Structure

## Top-Level Layout

```text
.
├── README.md
├── docs/
├── frontends/
├── migrations/tenant/
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
- `frontends/`: frontend workspace with browser applications and shared frontend packages.

## Frontends Layout

```text
frontends/
├── apps/
│   ├── console/
│   └── shortlink/
└── packages/
    ├── api-client/
    ├── config/
    └── ui/
```

- `frontends/apps/console/`: Vue 3 administrative and operator console application.
- `frontends/apps/shortlink/`: short link frontend experience.
- `frontends/packages/api-client/`: shared backend HTTP API client package.
- `frontends/packages/config/`: shared frontend configuration package.
- `frontends/packages/ui/`: shared frontend UI package.

## Modules Layout

```text
src/modules/
├── tenancy/
├── identity/
├── inventory/
└── shared/
```

## Common Module Shape

- `domain/`: entities, value objects, repository protocols, domain errors.
- `application/`: use cases, DTOs, commands, queries, application services.
- `infrastructure/`: persistence, adapters and integrations.
- `presentation/`: HTTP routers and dependency assembly.

Modules may further split these layers by subdomain when the module owns more
than one closely related concept. For example, `tenancy` now separates
`tenant` and `tenant_domain` inside both `domain/` and `application/`.

`shared` uses the same four layer roots, but each layer is split by feature
aggregate: `events`, `persistence`, `identity_context`, `value_object`,
`errors`, `email`, `tokens`, `time`, `uuid`, `access` and `http`. Shared layer
roots contain only `__init__.py`; class/protocol/model files live under those
aggregate folders.

`identity` similarly separates `user` and `auth`: `domain/user/` owns user and
email state, while `domain/auth/` owns OTP/session errors and
`application/auth/` contains console auth command/dto/service/use case files.
Its infrastructure uses repositories, adapters and persistence models without a
separate mapper layer; ORM -> domain mapping is performed explicitly in the
repository return paths.

`inventory` currently defines Warehouse domain/persistence and a repository protocol. Static tenant revision files live in `migrations/tenant/versions/`.

## Management Layout

- `src/management/cli.py`: parser and command dispatch.
- `src/management/commands/`: concrete command namespaces.

## Related

- [Architecture overview](overview.md)
- [Modules](../modules/tenancy.md)
- [Management CLI](../interfaces/management-cli.md)
- [Console frontend](../frontends/console.md)

## Source Of Truth

- `src/modules/`
- `src/management/`
- `test/`
- `frontends/`
