# Runtime management contract

This directory will contain the versioned OpenAPI/JSON Schema contract between
Control Plane and Runtime Core. Neither application may import the other's
domain or persistence code.

Initial contract surface:

```text
POST   /management/v1/tenants
GET    /management/v1/tenants/{external_id}
PATCH  /management/v1/tenants/{external_id}/status
DELETE /management/v1/tenants/{external_id}
PUT    /management/v1/tenants/{external_id}/domains/{external_domain_id}
DELETE /management/v1/tenants/{external_id}/domains/{external_domain_id}
GET    /management/v1/installation/capabilities
GET    /management/v1/installation/health
```

Mutations require `Idempotency-Key`, installation-scoped authentication and a
stable operation ID. The generated client belongs here; handwritten imports
between applications are forbidden.
