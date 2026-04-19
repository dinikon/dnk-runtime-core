# Request Lifecycle

## HTTP Request Flow

1. FastAPI app is created in `src/app_factory.py`.
2. Root router from `src/modules/router.py` is mounted under `/api`.
3. Module router selects the concrete controller function.
4. `presentation/depends/*` resolves use case and infrastructure dependencies.
5. Controller maps request schema to command/query DTO.
6. Application use case orchestrates services.
7. Domain services and repositories perform business work.
8. Response schema is built and returned to the client.

## Example Paths

- `POST /api/admin/create-tenant`
    - tenancy controller
    - tenancy use case
    - identity provisioning
    - schema bootstrap through tenancy-owned port
- `POST /api/crm/contacts`
    - authenticated request context
    - CRM contact use case
    - contact domain service
- `POST /api/console/auth/request-otp`
    - host extraction
  - identity controller in `presentation/http/console_auth/controller/`
    - identity OTP use case
  - tenancy host resolution and token/session infrastructure

## Management Flow

1. User runs `dnk-manage ...`.
2. `src/management/cli.py` builds parser and selects handler.
3. Handler opens one `UnitOfWork`.
4. Command-specific builder assembles use case graph from the same `uow.session`.
5. Use case runs and returns result or raises domain/application error.
6. `UnitOfWork.__aexit__` commits on success or rolls back on exception.

## Related

- [Dependency injection](dependency-injection.md)
- [Persistence and Unit of Work](persistence-and-uow.md)
- [HTTP API](../interfaces/http-api.md)
- [Management CLI](../interfaces/management-cli.md)

## Source Of Truth

- `src/app_factory.py`
- `src/modules/router.py`
- `src/management/cli.py`
