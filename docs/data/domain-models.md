# Domain Models

This page maps the main business entities that currently appear in the service.

## Tenancy

### `Tenant`

- Module owner: `tenancy`
- Business meaning: tenant account / workspace identity
- Key fields:
    - `id`
    - `name`
    - `external_id`
    - `status`
    - `custom_config`
    - timestamps

### `TenantDomain`

- Module owner: `tenancy`
- Business meaning: tenant host binding for a specific service surface
- Key fields:
    - `tenant_id`
    - `service_type`
    - `kind`
    - `host`
    - `status`
    - `is_primary`
    - verification/TLS fields

## Identity

### `User`

- Module owner: `identity`
- Business meaning: tenant-scoped console user
- Key fields:
    - `id`
    - `tenant_id`
    - `status`
    - name fields
    - locale/theme/timezone
    - last activity/login fields
    - `emails`

### `UserEmail`

- Module owner: `identity`
- Business meaning: user email identity and verification record
- Key fields:
    - `user_id`
    - `email`
    - `is_primary`
    - `is_verified`
    - `is_deleted`

## CRM

### `ContactEntity`

- Module owner: `crm`
- Business meaning: CRM contact record
- Key fields:
    - `id`
    - timestamps
    - `contact_name` with last/first/middle name

## Schema Registry

### `DataSourceEntity`

- Module owner: `schema_registry`
- Business meaning: tenant runtime data source metadata
- Key fields:
    - `id`
    - `tenant_id`
    - `data_source_type`
    - `schema_name`
    - `connection_dsn`
    - timestamps

### `ObjectEntity`

- Module owner: `schema_registry`
- Business meaning: runtime object metadata inside a tenant schema
- Key fields:
    - `id`
    - `tenant_id`
    - `data_source_id`
    - `object_name`
    - `object_label`
    - `description`
    - `fields`

### `FieldEntity`

- Module owner: `schema_registry`
- Business meaning: metadata for one runtime field inside one object
- Key fields:
    - `id`
    - `object_id`
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
- [Schema Registry module](../modules/schema-registry.md)

## Source Of Truth

- `src/modules/tenancy/domain/tenant/entity.py`
- `src/modules/tenancy/domain/tenant_domain/entity.py`
- `src/modules/identity/domain/entities.py`
- `src/modules/crm/domain/contact/entity.py`
- `src/modules/schema_registry/domain/datasource/entity.py`
- `src/modules/schema_registry/domain/object/entity.py`
