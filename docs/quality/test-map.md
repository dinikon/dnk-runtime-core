# Test Map

Run `uv run python -m unittest discover -s test -p 'test_*.py' -v`.

| Area | Coverage |
|---|---|
| Architecture | `test_architecture_boundaries.py`, `test_removed_module_boundaries.py`: layer directions, no imports/routes for removed dynamic modules |
| Inventory | `test_inventory_warehouse.py`: ids, title, roots/children, self-parent, tenant-only metadata |
| Tenancy | `test_tenancy_create_tenant_use_case.py`, `test_tenant_schema_bootstrap_boundary.py`, tenancy repository/resolve tests |
| Migrations CLI | `test_tenant_migrations_management.py`: target validation, batch failures and schema-name validation |
| PostgreSQL | `test_tenant_migrations_postgres.py`: migrations, constraints, isolation, onboarding rollback, autogenerate and concurrent processes |
| Identity | identity use-case/repository tests plus `test_identity_tenant_postgres.py`: tenant metadata, isolated reads/writes, FK constraints, administrator rollback and HTTP/DI login/profile/logout |
| Shared | database startup, email, messaging, outbox/inbox, jobs, pagination and UUID tests |

PostgreSQL tests require `TEST_POSTGRES_URL` pointing to a disposable PostgreSQL 16 database. They skip when unset; CI supplies a dedicated PostgreSQL service. Tests never use the application's configured database as a fallback.

Format/compile checks: `uv run black --check src test migrations` and `uv run python -m compileall src migrations`.
