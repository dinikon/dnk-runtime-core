# Domain Models

This page maps the main business entities that currently appear in the service.

Identifier convention: `EntityIdVO` is the single shared UUID primitive and the base class for concrete ids. Tenant
scope uses `EntityIdVO` directly; concrete entities expose concrete subclasses such as `UserIdVO`, `ContactIdVO`,
`ProductIdVO`, `CategoryIdVO`, `DataSourceIdVO`, `RuntimeObjectIdVO` and `RuntimeFieldIdVO`.

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

## CRM

### `ContactEntity`

- Module owner: `crm`
- Business meaning: CRM contact record
- Key fields:
    - `id` as `ContactIdVO`
    - timestamps
    - `contact_name` with last/first/middle name

## Inventory

### `ProductEntity`

- Module owner: `inventory`
- Business meaning: tenant-scoped physical good that can be sold
- Key fields:
    - `id` as `ProductIdVO`
    - timestamps
    - `sku`
    - `product_name`
    - `description`
    - `category_id` as `CategoryIdVO`

### `CategoryEntity`

- Module owner: `inventory`
- Business meaning: product category node in a tenant category tree
- Key fields:
    - `id` as `CategoryIdVO`
    - timestamps
    - `name`
    - `parent_category_id` as `CategoryIdVO`

## Schema Registry

### `DataSourceEntity`

- Module owner: `schema_registry`
- Business meaning: tenant runtime data source metadata
- Key fields:
    - `id` as `DataSourceIdVO`
    - `tenant_id` as `EntityIdVO`
    - `data_source_type`
    - `schema_name`
    - `connection_dsn`
    - timestamps

### `ObjectEntity`

- Module owner: `schema_registry`
- Business meaning: runtime object metadata inside a tenant schema
- Key fields:
    - `id` as `RuntimeObjectIdVO`
    - `tenant_id` as `EntityIdVO`
    - `data_source_id` as `DataSourceIdVO`
    - `object_name`
    - `object_label`
    - `description`
    - `fields`

### `FieldEntity`

- Module owner: `schema_registry`
- Business meaning: metadata for one runtime field inside one object
- Key fields:
    - `id` as `RuntimeFieldIdVO`
    - `object_id` as `RuntimeObjectIdVO`
    - `field_name`
    - `field_type`
    - `label`
    - `description`
    - `is_nullable`
    - `default_value`
    - `options`
    - `settings`

## Shared Kernel Concepts

### `Principal`

- Module owner: `shared`
- Business meaning: authenticated session identity bound to request context

### `RequestContext`

- Module owner: `shared`
- Business meaning: request-scoped envelope with principal, request id, IP and user agent

## Related

- [Runtime schema](runtime-schema.md)
- [Tenancy module](../modules/tenancy.md)
- [Identity module](../modules/identity.md)
- [CRM module](../modules/crm.md)
- [Inventory module](../modules/inventory.md)
- [Schema Registry module](../modules/schema-registry.md)

## Source Of Truth

- `src/modules/tenancy/domain/tenant/entity.py`
- `src/modules/tenancy/domain/tenant_domain/entity.py`
- `src/modules/identity/domain/user/entity.py`
- `src/modules/identity/domain/auth/error.py`
- `src/modules/crm/domain/contact/entity.py`
- `src/modules/inventory/domain/product/entity.py`
- `src/modules/inventory/domain/category/entity.py`
- `src/modules/schema_registry/domain/datasource/entity.py`
- `src/modules/schema_registry/domain/object/entity.py`
