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
| Control Plane v1 | `test_control_plane_runtime.py`: durable acceptance, concurrency, fencing, rollback, readiness, queue recovery and monotonic access delivery |
| Global migrations | `test_global_migrations_postgres.py`: fresh baseline, current schema check and refusal to adopt an unversioned database |
| Management trust | `test_management_trust_boundary.py`: socket peer, mTLS fingerprint, Host isolation, forwarded headers and access-log redaction |
| Cloud identity/access | `test_identity_cloud.py`, `test_identity_access_postgres.py`, `test_identity_csrf.py`, `test_identity_redis.py`: OIDC checks, state replay, OTP invitations, roles, last admin, session epochs and atomic Redis consumption |
| Core interoperability | `test_identity_core_interop.py`: real Core authorization/token/JWKS, key rotation, explicit link without TenantAccess and local revoke; optional HTTPS transport |
| Live HTTPS installation | `test/integration/runtime_https.py`: actual Core RuntimeClient, nginx mTLS, two zones, duplicate commands, API/worker restart and durable recovery |

Integration tests require disposable services. `TEST_POSTGRES_URL` selects tenant/identity PostgreSQL, `TEST_CP_POSTGRES_URL` selects the Control Plane test database, and `DNK_TEST_DATABASE_URL` selects the global migration/scheduled-job test database. `TEST_REDIS_URL` and `TEST_CP_RABBITMQ_URL` enable real atomic consumption and broker delivery. The existing CI checks create and clean up these services and supply all five variables. Tests never use the application's database as a fallback.

Set `CORE_REPOSITORY_PATH` to an installed Core checkout to include cross-repository OIDC tests. Core runs with its real Django implementation and a disposable SQLite test database; Runtime uses PostgreSQL. HTTPS mode also accepts `CORE_INTEROP_BIND`, `CORE_INTEROP_PUBLIC_ORIGIN` and `CORE_INTEROP_CA_FILE` for a test TLS proxy. The separate live installation harness and release checks are documented in [Control Plane deployment](../deployment/control-plane-v1.md).

Format/compile checks: `uv run black --check src test migrations` and `uv run python -m compileall src migrations`.
