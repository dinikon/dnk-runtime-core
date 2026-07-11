# Tenancy

Owns the global `Tenant`, `TenantMembership`, roles, owner transfer and lifecycle
state. It enforces exactly one active owner, performs transfer under a database
lock, requires recent authentication and emits an immutable audit event.

Runtime tenants are projections addressed by the global tenant ID through
`RuntimeTenant.external_id`.
