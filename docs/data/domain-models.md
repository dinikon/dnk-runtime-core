# Domain Models

This page maps the main business entities that currently appear in the service.

Identifier convention: `EntityIdVO` is the single shared UUID primitive and the base class for concrete ids. Tenant
scope uses `EntityIdVO` directly; concrete entities expose concrete subclasses such as `UserIdVO`, `ContactIdVO`,
`CompanyIdVO`, `DataSourceIdVO`, `RuntimeObjectIdVO` and `RuntimeFieldIdVO`.

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

### `CompanyEntity`

- Module owner: `crm`
- Business meaning: CRM company record
- Key fields:
    - `id` as `CompanyIdVO`
    - timestamps
    - `legal_name`

## Communication

### `ProviderConnector`

- Module owner: `communication`
- Business meaning: tenant-local provider YAML connector definition
- Key fields:
    - `provider_connector_id` as `ProviderConnectorIdVO`
    - provider code/name/version/type
    - YAML spec/checksum
  - status (`ACTIVE`, `DISABLED`, `ARCHIVED`) and timestamps

### `ProviderConnection`

- Module owner: `communication`
- Business meaning: tenant provider configuration and write-only credentials
- Key fields:
    - `provider_connection_id` as `ProviderConnectionIdVO`
    - `tenant_id` as `EntityIdVO`
    - `provider_connector_id` as `ProviderConnectorIdVO`
    - connection code/name/channel
  - config, secret ref, encoded secrets and status (`ACTIVE`, `DISABLED`, `ARCHIVED`)

### `MessageTemplate` And `TemplateVersion`

- Module owner: `communication`
- Business meaning: provider-bound message template and versioned payload
- Key fields:
    - `template_id` as `MessageTemplateIdVO`
    - `template_version_id` as `TemplateVersionIdVO`
    - provider connector/message type ids
    - channel, message class, status and active version metadata
    - template payload and variables schema

### `CommunicationRequest` And `OutboundMessage`

- Module owner: `communication`
- Business meaning: accepted send command and concrete provider outbound message
- Key fields:
    - `communication_request_id` as `CommunicationRequestIdVO`
    - `outbound_message_id` as `OutboundMessageIdVO`
    - tenant, template/version, connection and optional contact ids
    - recipient, variables, rendered payload and provider request snapshot
    - internal/external statuses, errors, queue/processing timestamps and retry state

### `DeliveryAttempt` And `DeliveryEvent`

- Module owner: `communication`
- Business meaning: provider send attempt history and webhook/status events
- Key fields:
    - `delivery_attempt_id` as `DeliveryAttemptIdVO`
    - `delivery_event_id` as `DeliveryEventIdVO`
    - outbound/connection ids
    - request/response snapshots, HTTP status, provider ids/statuses and event timestamps

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

## Custom Object

`custom_object` does not define a separate persistence entity for object metadata. It manages only runtime record rows
for descriptors whose `ObjectEntity.kind` is `custom`.

Schema metadata and DDL for custom objects and custom fields are managed by `schema_registry` config APIs.

Each custom object has system fields `id`, `created_at` and `updated_at`.

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
- [Communication module](../modules/communication.md)
- [Schema Registry module](../modules/schema-registry.md)

## Source Of Truth

- `src/modules/tenancy/domain/tenant/entity.py`
- `src/modules/tenancy/domain/tenant_domain/entity.py`
- `src/modules/identity/domain/user/entity.py`
- `src/modules/identity/domain/auth/error.py`
- `src/modules/crm/domain/contact/entity.py`
- `src/modules/crm/domain/company/entity.py`
- `src/modules/communication/domain/models.py`
- `src/modules/schema_registry/domain/datasource/entity.py`
- `src/modules/schema_registry/domain/object/entity.py`
