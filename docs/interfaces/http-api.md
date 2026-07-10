# HTTP API

All public HTTP routes are mounted under `/api`.

## Tenancy

| Method | Path                           | Module    | Request                          | Response                          | Auth                         | Main errors                                              |
|--------|--------------------------------|-----------|----------------------------------|-----------------------------------|------------------------------|----------------------------------------------------------|
| `POST` | `/api/admin/create-tenant`     | `tenancy` | `AdminCreateTenantRequestSchema` | `AdminCreateTenantResponseSchema` | Control-plane bearer API key | `401`, `409`, `422`, `500` if API key is not configured  |
| `GET`  | `/api/console/tenants/resolve` | `tenancy` | query from request host          | `ResolveTenantResponseSchema`     | none                         | normal not-found/availability is encoded in response DTO |

`ResolveTenantResponseSchema` includes `tenant_id`, `tenant_name`, `status`, and `api_host` when a tenant is found; missing tenants return nullable tenant fields.

## Communication

| Method   | Path                                                                        | Module          | Request / Params                              | Response                                | Auth                          | Main errors                |
|----------|-----------------------------------------------------------------------------|-----------------|-----------------------------------------------|-----------------------------------------|-------------------------------|----------------------------|
| `POST`   | `/api/communication/providers/connectors/import-yaml`                       | `communication` | `ImportYamlRequestSchema`                     | `ProviderConnectorResponseSchema`       | authenticated request context | `401`, `404`, `409`, `422` |
| `GET`    | `/api/communication/providers/connectors`                                   | `communication` | none                                          | `ListProviderConnectorsResponseSchema`  | authenticated request context | `401`, `409`, `422`        |
| `PATCH`  | `/api/communication/providers/connectors/{provider_connector_id}/status`    | `communication` | `UpdateProviderConnectorStatusRequestSchema`  | `ProviderConnectorResponseSchema`       | authenticated request context | `401`, `404`, `409`, `422` |
| `DELETE` | `/api/communication/providers/connectors/{provider_connector_id}`           | `communication` | path `provider_connector_id`                  | empty `204`                             | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/communication/providers/connections`                                  | `communication` | `CreateProviderConnectionRequestSchema`       | `ProviderConnectionResponseSchema`      | authenticated request context | `401`, `404`, `409`, `422` |
| `GET`    | `/api/communication/providers/connections`                                  | `communication` | none                                          | `ListProviderConnectionsResponseSchema` | authenticated request context | `401`, `409`, `422`        |
| `PATCH`  | `/api/communication/providers/connections/{provider_connection_id}/status`  | `communication` | `UpdateProviderConnectionStatusRequestSchema` | `ProviderConnectionResponseSchema`      | authenticated request context | `401`, `404`, `409`, `422` |
| `DELETE` | `/api/communication/providers/connections/{provider_connection_id}`         | `communication` | path `provider_connection_id`                 | empty `204`                             | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/communication/templates`                                              | `communication` | `CreateMessageTemplateRequestSchema`          | `MessageTemplateResponseSchema`         | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/communication/templates/{template_id}/versions`                       | `communication` | `CreateTemplateVersionRequestSchema`          | `TemplateVersionResponseSchema`         | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/communication/templates/{template_id}/versions/{version_id}/activate` | `communication` | path ids                                      | `TemplateVersionResponseSchema`         | authenticated request context | `401`, `404`, `409`, `422` |
| `GET`    | `/api/communication/templates`                                              | `communication` | none                                          | `ListMessageTemplatesResponseSchema`    | authenticated request context | `401`, `409`, `422`        |
| `POST`   | `/api/communication/send`                                                   | `communication` | `SendCommunicationRequestSchema`              | `SendCommunicationResponseSchema`       | authenticated request context | `401`, `404`, `409`, `422` |
| `GET`    | `/api/communication/messages`                                               | `communication` | `limit`, `offset`                             | `ListOutboundMessagesResponseSchema`    | authenticated request context | `401`, `409`, `422`        |
| `GET`    | `/api/communication/messages/{outbound_message_id}`                         | `communication` | path `outbound_message_id`                    | `OutboundMessageResponseSchema`         | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/communication/webhooks/{tenant_id}/{provider_code}`                   | `communication` | raw provider JSON payload                     | `WebhookResponseSchema`                 | optional request context      | `404`, `409`, `422`        |

## Schema Config

Schema config read routes use `POST` bodies instead of `GET`.

| Method   | Path                                   | Module            | Request / Params                           | Response                                 | Auth                          | Main errors                |
|----------|----------------------------------------|-------------------|--------------------------------------------|------------------------------------------|-------------------------------|----------------------------|
| `POST`   | `/api/config/objects/list`             | `schema_registry` | none                                       | `ListCustomObjectsResponseSchema`        | authenticated request context | `401`, `409`, `422`        |
| `POST`   | `/api/config/objects/create`           | `schema_registry` | `CreateCustomObjectRequestSchema`          | `CustomObjectResponseSchema`             | authenticated request context | `401`, `409`, `422`        |
| `DELETE` | `/api/config/objects/delete`           | `schema_registry` | body `object_id`                           | empty `204`                              | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/config/objects/schema`           | `schema_registry` | body `object_id`                           | `CustomObjectResponseSchema`             | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/config/objects/fields/create`    | `schema_registry` | `CreateCustomFieldRequestSchema`           | `CustomObjectResponseSchema`             | authenticated request context | `401`, `404`, `409`, `422` |
| `DELETE` | `/api/config/objects/fields/delete`    | `schema_registry` | body `object_id`, `field_id`               | `CustomObjectResponseSchema`             | authenticated request context | `401`, `404`, `409`, `422` |

Config rules:

- `system` and `view` objects are read-only.
- `standard` objects can receive/delete `custom` fields but cannot be deleted.
- `custom` objects can be created, deleted and extended with `custom` fields.
- `custom` object names are saved and returned with the `c_` prefix; create requests may omit it.
- `system` fields are hidden in config responses; `standard` fields are visible but not deletable.

## Custom Object

Custom object read routes use `POST` bodies instead of `GET`. The module owns only custom-object record CRUD.

| Method   | Path                                 | Module          | Request / Params                     | Response                          | Auth                          | Main errors                |
|----------|--------------------------------------|-----------------|--------------------------------------|-----------------------------------|-------------------------------|----------------------------|
| `POST`   | `/api/custom-objects/records/create` | `custom_object` | body `object_id`, `values`           | `CustomRecordResponseSchema`      | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/custom-objects/records/detail` | `custom_object` | body `object_id`, `row_id`           | `CustomRecordResponseSchema`      | authenticated request context | `401`, `404`, `409`, `422` |
| `POST`   | `/api/custom-objects/records/list`   | `custom_object` | body `object_id`, `filter`, `sort`   | `ListCustomRecordsResponseSchema` | authenticated request context | `401`, `404`, `409`, `422` |
| `PATCH`  | `/api/custom-objects/records/update` | `custom_object` | body `object_id`, `row_id`, `values` | `CustomRecordResponseSchema`      | authenticated request context | `401`, `404`, `409`, `422` |
| `PUT`    | `/api/custom-objects/records/update` | `custom_object` | body `object_id`, `row_id`, `values` | `CustomRecordResponseSchema`      | authenticated request context | `401`, `404`, `409`, `422` |
| `DELETE` | `/api/custom-objects/records/delete` | `custom_object` | body `object_id`, `row_id`           | empty `204`                       | authenticated request context | `401`, `404`, `409`, `422` |

## Identity / Console Auth

Mounted under `/api/console/auth`.

| Method  | Path                            | Module     | Request                                 | Response                             | Auth                 | Main errors                |
|---------|---------------------------------|------------|-----------------------------------------|--------------------------------------|----------------------|----------------------------|
| `POST`  | `/api/console/auth/request-otp` | `identity` | `RequestEmailOtpRequestSchema`          | `RequestEmailOtpResponseSchema`      | tenant host required | `403`, `404`               |
| `POST`  | `/api/console/auth/confirm-otp` | `identity` | `ConfirmEmailOtpRequestSchema`          | `ConfirmEmailOtpResponseSchema`      | tenant host required | `401`, `403`, `404`        |
| `GET`   | `/api/console/auth/me`          | `identity` | session cookie                          | `CurrentUserResponseSchema`          | session cookie       | `401`, `403`, `404`        |
| `PATCH` | `/api/console/auth/me`          | `identity` | `UpdateCurrentUserProfileRequestSchema` | `CurrentUserResponseSchema`          | session cookie       | `401`, `403`, `404`, `422` |
| `POST`  | `/api/console/auth/logout`      | `identity` | session cookie                          | `LogoutCurrentSessionResponseSchema` | session cookie       | `403`, `404`               |

## Notes

- Session cookie name comes from auth config and defaults to `dnk_session`.
- Identity routes are tenant-host aware, so host extraction is part of the authentication flow.
- Identity controllers map domain/tenancy errors directly inside controller files.
- Schema registry config and custom object routes do not accept `tenant_id` from the client. Controllers derive it
  from the request domain/auth context and pass it internally through commands/queries and use cases.
- `schema_registry` config routes and `custom_object` record routes follow the same tenant rule and accept runtime
  `object_id` / `row_id` in request bodies.
- `PATCH /api/console/auth/me` requires `interface_theme` and does not accept `null`.
- `GET /api/console/auth/me` and `PATCH /api/console/auth/me` always return `interface_theme` as a string.
- schema metadata/DDL changes are exposed only through `/api/config/...`; `custom_object` does not proxy those routes.
- communication routes return standard FastAPI error bodies with readable string `detail`; provider secrets are never
  returned by connection responses.

## Related

- [Management CLI](management-cli.md)
- [Tenancy module](../modules/tenancy.md)
- [Identity module](../modules/identity.md)
- [Communication module](../modules/communication.md)

## Source Of Truth

- `src/modules/router.py`
- `src/modules/tenancy/presentation/http/admin_tenant/controller/`
- `src/modules/tenancy/presentation/http/console_tenant/controller/`
- `src/modules/identity/presentation/http/console_auth/controller/`
- `src/modules/schema_registry/presentation/http/config/`
- `src/modules/custom_object/presentation/http/record/controller/`
