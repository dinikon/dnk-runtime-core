# Domain Models

This page maps the main business entities that currently appear in the service.

Identifier convention: `EntityIdVO` is the single shared UUID primitive and the base class for concrete ids. Tenant
scope uses `EntityIdVO` directly; concrete entities expose concrete subclasses such as `UserIdVO`,
`WarehouseIdVO`.

## Tenancy

### `Tenant`

- Module owner: `tenancy`
- Business meaning: tenant account / workspace identity
- Key fields:
    - `id` as `EntityIdVO`
    - `name`
    - `external_id`
    - `status`
    - `custom_config`
    - timestamps

### `TenantDomain`

- Module owner: `tenancy`
- Business meaning: tenant host binding for a specific service surface
- Key fields:
    - `id` as `TenantDomainIdVO`
    - `tenant_id` as `EntityIdVO`
    - `service_type`
    - `kind`
    - `host`
    - `status`
    - `is_primary`
    - verification/TLS fields

## Identity

- Structure note: `identity` splits user state into `domain/user/` and auth-specific
  OTP/session errors into `domain/auth/`.

### `User`

- Module owner: `identity`
- Business meaning: tenant-scoped console user
- Key fields:
    - `id` as `UserIdVO`
    - `tenant_id` as `EntityIdVO`
    - `status`
    - name fields
    - locale/theme/timezone
    - last activity/login fields
    - `emails`

### `UserEmail`

- Module owner: `identity`
- Business meaning: user email identity and verification record
- Key fields:
    - `id` as `UserEmailIdVO`
    - `user_id` as `UserIdVO`
    - `email`
    - `is_primary`
    - `is_verified`
    - `is_deleted`

## Inventory

`Warehouse` represents a physical warehouse with `WarehouseIdVO`, title, nullable parent id and audit fields. Storage uses a self-FK within each tenant schema. Multiple roots are allowed, self-parent is rejected, and deletion of a parent with children is restricted. Longer cycles are deferred to future hierarchy use cases.

## Shared Kernel Concepts

### `Principal`

- Module owner: `shared`
- Business meaning: authenticated session identity bound to request context

### `RequestContext`

- Module owner: `shared`
- Business meaning: request-scoped envelope with principal, request id, IP and user agent

## Related

- [Tenant migrations](tenant-migrations.md)
- [Tenancy module](../modules/tenancy.md)
- [Identity module](../modules/identity.md)
- [Inventory module](../modules/inventory.md)

## Source Of Truth

- `src/modules/tenancy/domain/tenant/entity.py`
- `src/modules/tenancy/domain/tenant_domain/entity.py`
- `src/modules/identity/domain/user/entity.py`
- `src/modules/identity/domain/auth/error.py`
