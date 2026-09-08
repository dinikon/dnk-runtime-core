# HTTP API

All public HTTP routes are mounted under `/api`.

## Tenancy

| Method | Path                           | Module    | Request                          | Response                          | Auth                         | Main errors                                              |
|--------|--------------------------------|-----------|----------------------------------|-----------------------------------|------------------------------|----------------------------------------------------------|
| `POST` | `/api/admin/create-tenant`     | `tenancy` | `AdminCreateTenantRequestSchema` | `AdminCreateTenantResponseSchema` | Control-plane bearer API key | `401`, `409`, `422`, `500` if API key is not configured  |
| `GET`  | `/api/console/tenants/resolve` | `tenancy` | query from request host          | `ResolveTenantResponseSchema`     | none                         | normal not-found/availability is encoded in response DTO |

`ResolveTenantResponseSchema` includes `tenant_id`, `tenant_name`, `status`, and `api_host` when a tenant is found; missing tenants return nullable tenant fields.

## Inventory

Inventory currently exposes no HTTP routes. Dynamic schema configuration routes were removed.

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
- `PATCH /api/console/auth/me` requires `interface_theme` and does not accept `null`.
- `GET /api/console/auth/me` and `PATCH /api/console/auth/me` always return `interface_theme` as a string.

## Related

- [Management CLI](management-cli.md)
- [Tenancy module](../modules/tenancy.md)
- [Identity module](../modules/identity.md)

## Source Of Truth

- `src/modules/router.py`
- `src/modules/tenancy/presentation/http/admin_tenant/controller/`
- `src/modules/tenancy/presentation/http/console_tenant/controller/`
- `src/modules/identity/presentation/http/console_auth/controller/`
