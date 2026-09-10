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
  - tenant context and token store ports
- `presentation/http/console_auth/`
    - controller/request/response files per endpoint
- `presentation/depends/`
    - `application.py` for use case wiring
    - `infrastructure.py` for repository/adapters/settings wiring

## Infrastructure / Persistence

- `UserModel` and `UserEmailModel` inherit `TenantBase`; Alembic owns `users` and `user_emails` in each tenant schema
- `users` has no SQL `tenant_id` column; `user_emails.user_id` references `users.id` in the same schema without cascading deletion
- `SqlAlchemyUserRepository` receives the active UoW session and `TenantSchemaNaming`; every operation requires an explicit tenant identifier
- Core statements use the models' `__table__` definitions and a per-statement `schema_translate_map`, preserving connection state and avoiding ORM identity collisions across tenants
- repository results are explicitly mapped to domain entities; `User.tenant_id` comes from the operation context
- add/profile writes reject a mismatch between the supplied tenant and `User.tenant_id` before executing SQL
- missing tenant schemas/tables produce infrastructure errors; there is no fallback to shared users
- startup global `create_all` does not create identity tables; onboarding migrates the tenant schema before creating its administrator
- token/session implementations use shared `TokenManager`
- tenant context is resolved through a tenancy-owned use case adapter
- request OTP delegates typed email sending to shared `EmailService`
- email delivery uses shared provider wiring with SMTP MVP transport and a placeholder `resend` provider

## Presentation / Entry Points

Console auth routes live under `/api/console/auth`:

- `POST /request-otp`
- `POST /confirm-otp`
- `GET /me`
- `PATCH /me`
- `POST /logout`

Each controller keeps its own explicit `try/except -> HTTPException` mapping.
`identity` does not use a shared `error_mapper.py`.
Current-user profile stores `interface_theme` as a non-null string.
The default theme is `system`, and `PATCH /me` requires an explicit non-null theme value.

## Auth Settings

- OTP code length
- OTP challenge TTL
- session TTL
- session cookie name
- email OTP response still returns `code` only in `DEVELOPMENT`
- in development mode, OTP code may be returned in response for easier local testing

## Dependencies On Other Modules

- uses `tenancy` host resolution rules and tenant availability checks
- uses `shared` request context, UoW and token abstractions
- is consumed by `tenancy` through `UserService` provisioning adapter

## Transition from shared users

This change requires recreating development/test databases and repeating tenant onboarding. Revision `0002_identity_users` creates empty tenant identity tables; it neither copies nor deletes legacy `public.users` and `public.user_emails`. Existing shared-user databases are not compatible with the new repository. HTTP contracts, OTP/session formats and email uniqueness behavior remain unchanged.

## Tests Covering This Module

- `test/test_identity_tenant_postgres.py`
    - identical IDs/emails in separate tenant schemas and isolated profile/email writes
    - local foreign keys, migration transitions and onboarding rollback after administrator insertion
    - HTTP login, profile updates, cross-tenant session rejection and logout with real repository/DI
- `test/test_identity_use_cases.py`
    - auth use cases and tenant admin provisioning service
- `test/test_identity_http_router.py`
    - public route registration
    - cookie behavior
  - per-controller HTTP error mapping
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
