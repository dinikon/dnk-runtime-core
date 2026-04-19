# Identity Module

## Purpose

`identity` provides tenant-aware console authentication, current-user profile
read/update flows, and tenant admin provisioning during onboarding.

## Public Functionality

- request email OTP
- confirm OTP and establish session
- load current user by session
- update current user profile
- logout current session
- provision tenant admin user during onboarding

## Main Flows / Use Cases

- `RequestEmailOtpUseCase.__call__`
- `ConfirmEmailOtpUseCase.__call__`
- `AuthenticateBySessionUseCase.__call__`
- `GetCurrentUserUseCase.__call__`
- `UpdateCurrentUserProfileUseCase.__call__`
- `LogoutCurrentSessionUseCase.__call__`
- `UserService.create_tenant_admin`

## Internal Structure

- `domain/user/`
    - `entity.py` with `User` and `UserEmail`
    - `error.py` with user/email login errors
    - `repository.py` with `UserRepositoryProtocol`
- `domain/auth/`
    - `error.py` with OTP/session errors
- `application/auth/`
    - `command/`, `dto/`, `service/`, `use_case/`
- `application/user/`
    - `dto/`, `service/`
- `application/ports/`
    - tenant context, token store and email sender ports
- `presentation/http/console_auth/`
    - controller/request/response files per endpoint
- `presentation/depends/`
    - `application.py` for use case wiring
    - `infrastructure.py` for repository/adapters/settings wiring

## Infrastructure / Persistence

- SQLAlchemy repositories store users and user emails
- `SqlAlchemyUserRepository` explicitly maps ORM models to domain entities in its `return`
- token/session implementations use shared `TokenManager`
- tenant context is resolved through a tenancy-owned use case adapter
- email delivery currently uses an in-memory stub adapter by default

## Presentation / Entry Points

Console auth routes live under `/api/console/auth`:

- `POST /request-otp`
- `POST /confirm-otp`
- `GET /me`
- `PATCH /me`
- `POST /logout`

Each controller keeps its own explicit `try/except -> HTTPException` mapping.
`identity` does not use a shared `error_mapper.py`.

## Auth Settings

- OTP code length
- OTP challenge TTL
- session TTL
- session cookie name
- in development mode, OTP code may be returned in response for easier local testing

## Dependencies On Other Modules

- uses `tenancy` host resolution rules and tenant availability checks
- uses `shared` request context, UoW and token abstractions
- is consumed by `tenancy` through `UserService` provisioning adapter

## Tests Covering This Module

- `test/test_identity_use_cases.py`
    - auth use cases and tenant admin provisioning service
- `test/test_identity_http_router.py`
    - public route registration
    - cookie behavior
  - per-controller HTTP error mapping
- `test/test_identity_repository.py`
    - explicit ORM -> domain mapping in repository return paths
- `test/test_architecture_boundaries.py`
    - forbids legacy identity import paths
  - forbids removed `error_mapper` and `infrastructure.mapper` imports

## Related

- [HTTP API](../interfaces/http-api.md)
- [Configuration](../interfaces/configuration.md)
- [Domain models](../data/domain-models.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/identity/presentation/http/console_auth/controller/`
- `src/modules/identity/domain/user/entity.py`
- `src/modules/identity/domain/auth/error.py`
- `src/modules/identity/application/auth/use_case/`
- `src/modules/identity/application/user/service/user_service.py`
- `src/config/feature/identity/auth_config.py`
