# Tenancy

Tenancy owns tenant accounts, domain bindings, host resolution, onboarding, tenant-schema infrastructure and admission.

## Public flows

- Creation is invoked by the durable [Control Plane installer](control-plane.md); the former bearer-key endpoint is removed.
- `GET /api/console/tenants/resolve`: resolves the incoming host and tenant availability.

Runtime UUIDs are reserved before installation. New installations remain `provisioning` until local verification and activation commit. Exact host bindings have a global unique constraint; display names may repeat.

## Domain and persistence

`Tenant` and `TenantDomain` have their domain entities, typed ids, repository protocols, global SQLAlchemy models and explicit mappers. Identity provisioning uses a tenancy-owned port implemented by the identity adapter.

## Schema bootstrap

`TenantSchemaBootstrapContext` contains `tenant_id` and `schema_name`. Its factory delegates to the Tenancy-owned `TenantSchemaNaming`: configured prefix plus UUID hex.

`TenantSchemaBootstrapPort` is implemented by `AlembicTenantSchemaBootstrapAdapter`. It uses the current UoW session, locks the target schema, rejects an existing schema, creates it and runs tenant migrations. There is no seed, datasource metadata or dynamic schema dependency.

Administrator provisioning runs only after schema bootstrap succeeds. The whole onboarding operation commits together or rolls back together, including failures after administrator insertion. A schema-name conflict is a tenancy error mapped to HTTP 409. Technical migration errors remain server errors.

## Tenant Infrastructure

`application/tenant/tenant_schema_naming.py` defines deterministic schema naming;
`tenant_admission.py` defines `TenantUnavailable` and the optional admission context.
`infrastructure/tenant/persistence/` owns `TenantBase`, `TENANT_SCHEMA_ALIAS`,
`TenantGate`, tenant migrations and migration metadata helpers.
`presentation/tenant/http/tenant_gate.py` owns `TenantAdmissionMiddleware`.

Admission checks tenant state and holds a PostgreSQL advisory lock through the request.
The middleware exposes `request.state.tenant_connection`; shared UoW reuses that connection
and finishes its transaction before sending the response. Jobs and Events remain in shared
and use these Tenancy admission components through direct imports.

All Tenancy `__init__.py` files are empty. Consumers and model registrars import definition files.
The physical migrations directory, revision history, schema alias and SQL metadata are unchanged.

## Presentation and management

HTTP DI is assembled in `presentation/depends`. Migration CLI composition lives in `presentation/depends/management.py`; it reads existing tenant identifiers and processes one tenant per UoW. Existing schemas are required by management commands.

## Tests

Unit tests cover orchestration, host resolution and the bootstrap boundary. PostgreSQL integration tests verify successful onboarding, schema-conflict handling and complete rollback after migration or administrator provisioning failure.

## Related

- [Inventory](inventory.md)
- [Identity](identity.md)
- [Tenant migrations](../data/tenant-migrations.md)
- [HTTP API](../interfaces/http-api.md)
