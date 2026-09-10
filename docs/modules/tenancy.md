# Tenancy

Tenancy owns tenant accounts, domain bindings, host resolution and onboarding.

## Public flows

- `POST /api/admin/create-tenant`: control-plane bearer authentication; creates tenant and primary domain, bootstraps the tenant schema to Alembic head, then creates its administrator and email inside that schema.
- `GET /api/console/tenants/resolve`: resolves the incoming host and tenant availability.

Request and response contracts are unchanged by the introduction of Inventory.

## Domain and persistence

`Tenant` and `TenantDomain` have their domain entities, typed ids, repository protocols, global SQLAlchemy models and explicit mappers. Identity provisioning uses a tenancy-owned port implemented by the identity adapter.

## Schema bootstrap

`TenantSchemaBootstrapContext` contains `tenant_id` and `schema_name`. Its factory delegates to the shared `TenantSchemaNaming`: configured prefix plus UUID hex.

`TenantSchemaBootstrapPort` is implemented by `AlembicTenantSchemaBootstrapAdapter`. It uses the current UoW session, locks the target schema, rejects an existing schema, creates it and runs tenant migrations. There is no seed, datasource metadata or dynamic schema dependency.

Administrator provisioning runs only after schema bootstrap succeeds. The whole onboarding operation commits together or rolls back together, including failures after administrator insertion. A schema-name conflict is a tenancy error mapped to HTTP 409. Technical migration errors remain server errors.

## Presentation and management

HTTP DI is assembled in `presentation/depends`. Migration CLI composition lives in `presentation/depends/management.py`; it reads existing tenant identifiers and processes one tenant per UoW. Existing schemas are required by management commands.

## Tests

Unit tests cover orchestration, host resolution and the bootstrap boundary. PostgreSQL integration tests verify successful onboarding, schema-conflict handling and complete rollback after migration or administrator provisioning failure.

## Related

- [Inventory](inventory.md)
- [Identity](identity.md)
- [Tenant migrations](../data/tenant-migrations.md)
- [HTTP API](../interfaces/http-api.md)
