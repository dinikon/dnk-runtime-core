# Control Plane domain glossary

## Aggregate ownership

| Term | Meaning | Owner module | Main relationships |
| --- | --- | --- | --- |
| `UserAccount` | Global human identity | `identity_access` | Has profile, contacts, sessions and external identities |
| `Customer` | Commercial/legal customer | `customers` | Has users and one or more tenants |
| `Tenant` | Technical workspace | `tenancy` | Belongs to exactly one customer |
| `TenantMembership` | User access to a tenant | `tenancy` | Belongs to one tenant and one user account |
| `Installation` | One Runtime Core installation | `installations` | Cluster or Single/Box mode |
| `TenantPlacement` | Tenant deployment on an installation | `installations` | Links global tenant to local runtime tenant |
| `DomainBinding` | Hostname assigned to a tenant service | `domains` | Follows the tenant's current placement |
| `ProvisioningOperation` | Observable long-running workflow | `provisioning` | Owns steps, retries and terminal result |

## Ownership invariant

`Tenant.owner_membership_id` identifies the one active owner membership. Owner
is an effective role, not an independent user reference. The membership keeps
`ADMIN` as its fallback role, so the previous owner becomes admin after a
successful transfer. Creating a tenant and its first owner membership is one
transaction; transfer locks the tenant and both memberships.

## Identity and lifecycle boundaries

- Global Control Plane identity is independent from Runtime tenant-local users.
- Customer ownership/billing and tenant ownership are different concepts.
- A tenant has one customer but can have multiple historical placements.
- A placement carries desired and observed Runtime state.
- Domain ownership/verification belongs to Control Plane; host routing in
  Runtime is a local projection.
- Billing belongs to Customer and never becomes a field of Runtime tenant data.
- Audit is append-only evidence, not a source of business state.

## Dependency direction

Business modules may depend on `shared` technical primitives. Cross-module use
cases communicate through application ports and stable IDs. Domain/application
layers never import infrastructure/presentation layers, and no Control Plane
module imports Runtime Core code.
