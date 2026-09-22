# HTTP API

## Management protocol v1

Management routes are served only on the Runtime management hostname through mTLS. The application checks the unmodified socket peer, Host and Core certificate fingerprint before interpreting proxy headers. Responses are direct JSON objects without a `data` envelope.

Versioned [JSON schemas and synthetic examples](../contracts/runtime-v1/README.md) describe the exact request/response shapes and include regeneration and contract-test commands.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/internal/v1/status/` | `ready`, `protocol_version: 1`, `domains` with separate routing/TLS observations |
| POST | `/internal/v1/tenant-provisioning/` | `202` after durable acceptance; `Idempotency-Key` equals `attempt_id` |
| GET | `/internal/v1/tenant-provisioning/{attempt_id}/` | Saved result, or `404` for an unknown record |
| GET | `/internal/v1/metrics/` | Prometheus integration metrics |

Commands contain `tenant_id`, `operation_id`, `attempt_id`, `hostname`, `name`, `owner: {sub, verified_email, profile}`, and `oidc: {issuer, client_id, client_secret, redirect_uri}`. Tenant and subject identifiers are Core UUIDs; Runtime reserves its own UUID before installation. Validation responses do not echo credentials.

Attempt responses contain `tenant_id`, `operation_id`, `attempt_id`, `state`, `resources_state`, `runtime_tenant_id` and a safe error code. States are `queued/running/succeeded/failed`; resource states are `absent/present/unknown`. Installation failures are saved results returned with HTTP `200`. Only verified `failed + absent` permits another attempt; a missing attempt does not prove resource absence. The former bearer-key creation endpoint has been removed.

## Readiness

| Method | Path | Result |
| --- | --- | --- |
| GET | `/.well-known/dnk/tenant-ready` | Ready: `200 {tenant_id, hostname, ready: true}`; unknown Host: `404`; incomplete: `503` |
| GET | `/.well-known/dnk/instance-routing` | Instance/hostname response only on reserved probe hosts |
| GET | `/health/live` | Process liveness; not published by ingress |
| GET | `/health/ready` | Current global database revision; not published by ingress |

Readiness never requests Core tokens. The routing probe is separate from a Tenant and cannot claim an installation is ready.

## Console identity and access

Tenant context comes from the exact request Host. Session cookies are host-only, Secure, HttpOnly and SameSite=Lax by default. Browser mutations require the exact Origin and `X-CSRF-Token` obtained from `/api/console/auth/csrf`. Fetch a fresh token after a session transition. OIDC callback uses its one-time state instead.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/console/tenants/resolve` | Workspace availability; unknown Host is `404` |
| GET | `/api/console/auth/csrf` | Anonymous or session-bound browser token |
| POST | `/api/console/auth/request-otp` | Existing active user's email |
| POST | `/api/console/auth/confirm-otp` | Confirm code and open local session |
| GET / PATCH | `/api/console/auth/me` | Current profile; response includes `role` |
| POST | `/api/console/auth/logout` | End local session |
| GET | `/api/console/users` | Admin; `{users: [...]}` |
| PATCH | `/api/console/users/{user_id}` | Admin; optional `role: admin/member`, `status: active/revoked` |
| GET / POST | `/api/console/invitations` | Admin; list or create `{email, role}` and receive `invitation_url` |
| DELETE | `/api/console/invitations/{invitation_id}` | Admin; revoke invitation |
| POST | `/api/console/invitations/request-otp` | `{invitation_token}`; code goes only to the invitation email |
| POST | `/api/console/invitations/accept` | `{invitation_token, token, code, first_name, last_name}`; create local user after OTP |
| GET | `/api/auth/cloud/status/` | `{enabled, linked}` |
| POST | `/api/auth/cloud/start/` | `{purpose: login/link}` → `{authorization_url}` |
| GET | `/api/auth/cloud/callback/` | Exact registered query callback; local login or explicit link |
| DELETE | `/api/auth/cloud/link/` | Unlink and invalidate local sessions |

Invitation links expire after seven days. Duplicate local email or cloud identity conflicts rather than merging accounts. Members cannot manage other users. The last active administrator cannot be revoked or demoted. Unlink preserves permitted OTP access. Local revocation takes effect without Core connectivity and old sessions do not revive when access is restored.

## Console CRM

CRM routes are tenant-scoped from the authenticated request context. Clients cannot choose a `tenant_id`. Every
authenticated tenant user can read and mutate CRM data; browser mutations require the shared CSRF token.

| Method | Path                                              | Behavior                                                   |
|--------|---------------------------------------------------|------------------------------------------------------------|
| GET    | `/api/console/crm/contacts?q=&limit=25&offset=0`  | Search and page contacts; `{items, total, limit, offset}`  |
| GET    | `/api/console/crm/contacts/{id}`                  | Get a contact or `404`                                     |
| POST   | `/api/console/crm/contacts`                       | Create a contact and return it with `201`                  |
| PUT    | `/api/console/crm/contacts/{id}`                  | Update a contact                                           |
| DELETE | `/api/console/crm/contacts/{id}`                  | Hard-delete a contact and return `204`                     |
| GET    | `/api/console/crm/companies?q=&limit=25&offset=0` | Search and page companies; `{items, total, limit, offset}` |
| GET    | `/api/console/crm/companies/{id}`                 | Get a company or `404`                                     |
| POST   | `/api/console/crm/companies`                      | Create a company and return it with `201`                  |
| PUT    | `/api/console/crm/companies/{id}`                 | Update a company                                           |
| DELETE | `/api/console/crm/companies/{id}`                 | Hard-delete a company and return `204`                     |

`limit` must be between 1 and 100. Search is case-insensitive; results use fixed name-then-id ordering. Domain
validation is `422`, missing records are `404`, and persistence conflicts are `409`. See [CRM](../modules/crm.md).

## Runtime to Core

The outbox sends Instance-mTLS `PUT /internal/v1/tenants/{tenant_id}/access/{user_id}/` with `{event_id, version, available}`. Core replies `{status: 200, data: {applied, version?}}`; both applied and already-processed results acknowledge delivery. Roles stay local.

See [Control Plane integration](../modules/control-plane.md), [Identity](../modules/identity.md) and [configuration](configuration.md).
