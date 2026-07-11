# Control Plane state machines

The canonical machine-readable transition catalog is
[`../../contracts/lifecycle/state-machines.yaml`](../../contracts/lifecycle/state-machines.yaml).
This document explains the business meaning of those transitions.

## Tenant

`DRAFT → PROVISIONING → ACTIVE` is the normal create flow. Provisioning failure
moves to `FAILED`; retry returns to `PROVISIONING`.

Suspension uses `ACTIVE → SUSPENDING → SUSPENDED`; failure returns to `ACTIVE`.
Resume uses `SUSPENDED → RESUMING → ACTIVE`; failure returns to `SUSPENDED`.

A confirmed delete request from any non-terminal state moves to
`DELETION_PENDING`, stores the previous stable state and disables login/write.
Cancellation within 30 days restores that state. Expiry moves to `DELETING`.
Cleanup failures keep the tenant in `DELETING` while the operation retries.
Only confirmed Runtime, DNS and Kubernetes cleanup permits `DELETED`.

## Provisioning operation

Operations start in `PENDING`, run in `RUNNING`, and end in `SUCCEEDED`,
`FAILED` or `CANCELLED`. Retryable failures use
`RUNNING → RETRY_SCHEDULED → RUNNING`. Cancellation is allowed only before an
irreversible step.

## Placement, domain and installation

Placement mirrors Runtime provisioning and is independent from global Tenant
status. Domain state exposes verification, DNS, route and TLS progress rather
than collapsing them into one boolean. Installation actual state is derived
from registration, heartbeat age, health and decommissioning observations;
Control Plane does not mark an installation offline merely because one request
failed.

## Owner transfer and agent command

Owner transfer is accepted only when still `PENDING`, unexpired, and the source
membership remains the current owner. Agent commands have one terminal outcome;
duplicate delivery returns the existing result instead of reopening the state
machine.
