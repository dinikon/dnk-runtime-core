# HTTP API

All public HTTP routes are mounted under `/api`.

## Tenancy

| Method | Path                           | Module    | Request                          | Response                          | Auth                         | Main errors                                              |
|--------|--------------------------------|-----------|----------------------------------|-----------------------------------|------------------------------|----------------------------------------------------------|
| `POST` | `/api/admin/create-tenant`     | `tenancy` | `AdminCreateTenantRequestSchema` | `AdminCreateTenantResponseSchema` | Control-plane bearer API key | `401`, `409`, `422`, `500` if API key is not configured  |
| `GET`  | `/api/console/tenants/resolve` | `tenancy` | query from request host          | `ResolveTenantResponseSchema`     | none                         | normal not-found/availability is encoded in response DTO |

## CRM

| Method   | Path                             | Module | Request                        | Response                     | Auth                          | Main errors         |
|----------|----------------------------------|--------|--------------------------------|------------------------------|-------------------------------|---------------------|
| `POST`   | `/api/crm/contacts`              | `crm`  | `CreateContactRequestSchema`   | `ContactResponseSchema`      | authenticated request context | `401`, `422`        |
| `POST`   | `/api/crm/contacts/fields`       | `crm`  | none                           | `ContactFieldsResponseSchema`| authenticated request context | `401`, `409`, `422` |
| `GET`    | `/api/crm/contacts`              | `crm`  | query params `limit`, `offset` | `ListContactsResponseSchema` | authenticated request context | `401`, `422`        |
| `GET`    | `/api/crm/contacts/{contact_id}` | `crm`  | path `contact_id`              | `ContactResponseSchema`      | authenticated request context | `401`, `404`, `422` |
| `PUT`    | `/api/crm/contacts/{contact_id}` | `crm`  | `UpdateContactRequestSchema`   | `ContactResponseSchema`      | authenticated request context | `401`, `404`, `422` |
| `DELETE` | `/api/crm/contacts/{contact_id}` | `crm`  | path `contact_id`              | empty `204`                  | authenticated request context | `401`, `404`, `422` |

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
- `schema_registry` currently has no public HTTP API surface.

## Related

- [Management CLI](management-cli.md)
- [Tenancy module](../modules/tenancy.md)
- [Identity module](../modules/identity.md)
- [CRM module](../modules/crm.md)

## Source Of Truth

- `src/modules/router.py`
- `src/modules/tenancy/presentation/http/admin_tenant/controller/`
- `src/modules/tenancy/presentation/http/console_tenant/controller/`
- `src/modules/identity/presentation/http/console_auth/controller/`
- `src/modules/crm/presentation/http/contact/controller/`
