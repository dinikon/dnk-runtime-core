# ADR-0002: Modular monolith deployment unit

- Status: Accepted
- Date: 2026-07-11

## Context

Control Plane needs HTTP APIs, background provisioning, reconciliation and
scheduled maintenance, but its domain boundaries do not yet require independent
microservice release cycles.

## Decision

- Control Plane is a modular monolith under one Python package.
- API, worker and scheduler share domain/application code and one container
  image.
- API, worker and scheduler have separate process entrypoints and Kubernetes
  workloads.
- Each bounded context uses `domain`, `application`, `infrastructure` and
  `presentation` layers when its first use case is implemented.
- Domain/application code cannot import infrastructure/presentation code.
- External systems are accessed through application-owned ports.
- A bounded context can be extracted only after an explicit ADR identifies an
  independent scaling, ownership or release requirement.

## Consequences

- One build artifact is promoted from preprod to production.
- Worker crashes cannot take down the API process.
- Module boundaries are protected by static architecture tests rather than by
  network boundaries.
