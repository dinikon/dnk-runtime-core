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
- `ResolveTenantByHostUseCase`
    - returns whether tenant exists and whether login is available
- `ResolveTenantRequestContextByHostUseCase`
    - builds tenant request context from incoming host

## Domain Model

- `Tenant`
    - tenant identity, name, external id, status, config and timestamps
- `TenantDomain`
    - host binding for a tenant, service type, status, verification and TLS mode

Current domain layout is split by subdomain:

- `domain/tenant/`
    - tenant entity, errors, repository contract, `TenantStatus`
- `domain/tenant_domain/`
    - tenant-domain entity, errors, repository contract and domain enums
- `domain/service/`
    - onboarding orchestration that creates `Tenant` + primary `TenantDomain`

## Infrastructure / Persistence

- SQLAlchemy repositories and mappers live under `tenancy/infrastructure/repository/` and
  `tenancy/infrastructure/mapper/`
- persistence stores tenant records and tenant domains
- module also contains identity provisioning adapter under `tenancy/infrastructure/adapter/`

## Presentation / Entry Points

- `POST /api/admin/create-tenant`
    - protected by control-plane bearer API key
- `GET /api/console/tenants/resolve`
    - resolves tenant availability by host and returns tenant id/name/status when found

Current HTTP layout is organized by endpoint area:

- `presentation/http/admin_tenant/`
    - controller, request and response schemas for admin create-tenant flow
- `presentation/http/console_tenant/`
    - controller and response schema for tenant resolve flow
- `presentation/depends/`
    - FastAPI DI builders for repositories, services and use cases

## Dependencies On Other Modules

- depends on `identity` through `IdentityProvisioningServiceProtocol`
- depends on `schema_registry` only through tenancy-owned `TenantSchemaBootstrapPort`
- relies on `shared` for request context, UoW and infrastructure

## Tests Covering This Module

- tenant creation orchestration and schema bootstrap boundary tests
- router smoke test for public tenancy endpoints
- architecture boundary test that prevents direct import of `schema_registry.application`

## Related

- [HTTP API](../interfaces/http-api.md)
- [Domain models](../data/domain-models.md)
- [Dependency injection](../architecture/dependency-injection.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/tenancy/application/tenant/use_case/create_tenant.py`
- `src/modules/tenancy/application/tenant_domain/use_case/resolve_tenant_by_host.py`
- `src/modules/tenancy/domain/tenant/entity.py`
- `src/modules/tenancy/domain/tenant_domain/entity.py`
- `src/modules/tenancy/application/ports/schema_bootstrap.py`
- `src/modules/tenancy/presentation/http/admin_tenant/controller/create_tenant.py`
- `src/modules/tenancy/presentation/http/console_tenant/controller/resolve_tenant.py`
