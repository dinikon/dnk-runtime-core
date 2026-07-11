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
├── backend/                   # FastAPI API, worker and scheduler codebase
├── frontend/                  # Separate Vue cabinet
├── contracts/                 # Versioned Control Plane ↔ Runtime contracts
├── deploy/helm/               # One chart with preprod/prod values
└── docs/
    └── IMPLEMENTATION_PLAN.md
```

Backend API and asynchronous workers should use the same Python package and
container image, but run as separate processes. Control Plane uses its own
PostgreSQL, Redis and messaging resources.

## Start here

Follow [the ordered implementation plan](docs/IMPLEMENTATION_PLAN.md). It
contains domain boundaries, state machines, API drafts, security requirements,
environment topology and acceptance criteria for every implementation phase.

## Minimal backend smoke test

From the repository root, after installing the backend dependencies:

```bash
PYTHONPATH=control-plane/backend/src \
  python -m unittest discover -s control-plane/backend/test -p "test_*.py" -v
```
