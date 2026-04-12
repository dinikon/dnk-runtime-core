# Tenancy Module

## Purpose

`tenancy` owns tenant lifecycle and tenant host resolution. It is the entry point for creating a tenant, provisioning
its primary console domain, and connecting onboarding to identity and runtime schema bootstrap.

## Public Functionality

- create tenant and primary console domain
- resolve tenant by host
- resolve request context by host for downstream auth/business flows

## Main Flows / Use Cases

- `CreateTenantUseCase`
    - creates `Tenant`
    - creates primary `TenantDomain`
    - provisions tenant admin through identity
    - bootstraps runtime schema through `TenantSchemaBootstrapPort`
- `ResolveTenantByHost`
    - returns whether tenant exists and whether login is available
- `ResolveTenantRequestContextByHost`
    - builds tenant request context from incoming host

## Domain Model

- `Tenant`
    - tenant identity, name, external id, status, config and timestamps
- `TenantDomain`
    - host binding for a tenant, service type, status, verification and TLS mode

## Infrastructure / Persistence

- SQLAlchemy repositories and persistence models live under `tenancy/infrastructure/`
- persistence stores tenant records and tenant domains
- module also contains identity provisioning adapter and host mapping logic

## Presentation / Entry Points

- `POST /api/admin/create-tenant`
    - protected by control-plane bearer API key
- `GET /api/console/tenants/resolve`
    - resolves tenant availability by host

## Dependencies On Other Modules

- depends on `identity` through `IdentityProvisioningServiceProtocol`
- depends on `schema_registry` only through tenancy-owned `TenantSchemaBootstrapPort`
- relies on `shared` for request context, UoW and infrastructure

## Tests Covering This Module

- tenant creation orchestration and schema bootstrap boundary tests
- host resolution endpoint and use case tests
- architecture boundary test that prevents direct import of `schema_registry.application`

## Related

- [HTTP API](../interfaces/http-api.md)
- [Domain models](../data/domain-models.md)
- [Dependency injection](../architecture/dependency-injection.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/tenancy/application/use_cases/create_tenant.py`
- `src/modules/tenancy/domain/entities.py`
- `src/modules/tenancy/application/ports/schema_bootstrap.py`
- `src/modules/tenancy/presentation/http/admin_tenants.py`
