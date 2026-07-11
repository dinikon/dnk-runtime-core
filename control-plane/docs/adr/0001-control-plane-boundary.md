# ADR-0001: Control Plane boundary

- Status: Accepted
- Date: 2026-07-11

## Context

Runtime Core owns tenant-local execution, schema and business data. Control
Plane owns global accounts, customers, tenant lifecycle, placements, domains and
desired infrastructure state. Sharing persistence or domain classes would make
Box installations depend on the central service and would couple releases.

## Decision

- Control Plane uses a dedicated PostgreSQL database and migration history.
- Control Plane never reads or writes Runtime Core tables.
- The two applications exchange versioned HTTP/agent contracts and integration
  events only.
- Control Plane is the source of desired state. Runtime and cluster agents are
  the source of observed actual state.
- Imports from Runtime Core's `src` package are forbidden in `control_plane`;
  imports from `control_plane` are forbidden in Runtime Core.
- ORM models, repositories, units of work and database sessions are not shared.
- Runtime user traffic must continue when Control Plane is unavailable.

The existing `CONTROL_PLANE_API_KEY` and `/api/admin/create-tenant` endpoint are
temporary legacy mechanisms. They remain unchanged in stage 0 and are replaced
by the signed Runtime Management contract during Runtime provisioning.

## Consequences

- Global tenant and domain rows are projections in Runtime, linked by stable
  external UUIDs.
- Cross-system changes are sagas with idempotency and reconciliation, never
  distributed database transactions.
- Contract compatibility is required before either application is upgraded.
