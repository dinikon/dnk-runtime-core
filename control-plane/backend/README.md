# Control Plane backend

The backend is a modular FastAPI application. API, worker and scheduler share
domain/application code but have separate entrypoints and Kubernetes workloads.

Every business module evolves toward this shape:

```text
<module>/
├── domain/            # entities, value objects, errors, repository contracts
├── application/       # commands, queries, DTOs, use cases, ports
├── infrastructure/    # PostgreSQL repositories and external adapters
└── presentation/      # HTTP, worker and management composition
```

Rules:

- no imports from the root Runtime Core `src/` package;
- no shared database with Runtime Core;
- domain/application layers do not import infrastructure/presentation;
- external calls are behind application-owned ports;
- every distributed mutation is idempotent and represented by an operation;
- database schema changes use Alembic from the first persistent entity.

The initial `app.py` only exposes `/health/live` and `/health/ready` so the
package boundary can be tested before business functionality is added.
