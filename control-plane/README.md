# DNK Control Plane

`control-plane` is an independent deployable application that owns global
accounts, customers, tenant lifecycle, ownership, installations, provisioning,
domains, DNS, Kubernetes desired state, audit and, later, billing.

It deliberately does not import domain entities, repositories or persistence
models from the root `dnk-runtime-core` application. Runtime Core remains the
data plane and executes idempotent management commands received from Control
Plane.

## Current state

This directory is an architectural scaffold. Only a minimal backend health
endpoint is present; business use cases, database migrations, frontend build and
Helm templates are intentionally scheduled in the implementation plan.

## Layout

```text
control-plane/
├── src/                       # FastAPI API, worker and scheduler package
├── test/                      # Backend tests
├── frontend/                  # Separate Vue cabinet
├── contracts/                 # Versioned Control Plane ↔ Runtime contracts
├── deploy/helm/               # One chart with preprod/prod values
├── pyproject.toml              # Python project and dependencies
└── docs/
    └── IMPLEMENTATION_PLAN.md
```

Backend API and asynchronous workers use the same Python package and
container image, but run as separate processes. Control Plane uses its own
PostgreSQL, Redis and messaging resources.

Every business module evolves toward this shape:

```text
<module>/
├── domain/            # entities, value objects, errors, repository contracts
├── application/       # commands, queries, DTOs, use cases, ports
├── infrastructure/    # PostgreSQL repositories and external adapters
└── presentation/      # HTTP, worker and management composition
```

The backend does not import Runtime Core's `src/` package or share its
database. Domain and application layers do not import infrastructure or
presentation code. External calls are kept behind application-owned ports,
and distributed mutations are idempotent operations.

## Start here

Follow [the ordered implementation plan](docs/IMPLEMENTATION_PLAN.md). It
contains domain boundaries, state machines, API drafts, security requirements,
environment topology and acceptance criteria for every implementation phase.

The accepted stage-0 baseline is documented in:

- [architecture decision records](docs/adr/);
- [domain glossary](docs/architecture/domain-glossary.md);
- [state machines](docs/architecture/state-machines.md);
- [threat model](docs/security/threat-model.md);
- [versioned contracts](contracts/README.md).

## Minimal backend smoke test

From the Runtime Core repository root:

```bash
uv run --project control-plane python -m unittest discover \
  -s control-plane/test -p "test_*.py" -v
```

Start the development API server with:

```bash
uv run --project control-plane fastapi dev control-plane/src/control_plane/app.py
```
