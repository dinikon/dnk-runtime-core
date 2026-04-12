# Identity Module

## Purpose

`identity` provides console authentication and session management. The current model is email OTP challenge + session
cookie for authenticated console users.

## Public Functionality

- request email OTP
- confirm OTP and establish session
- load current user by session
- update current user profile
- logout current session
- provision tenant admin user during onboarding

## Main Flows / Use Cases

- `RequestEmailOtp`
- `ConfirmEmailOtp`
- `AuthenticateBySession`
- `GetCurrentUser`
- `UpdateCurrentUserProfile`
- `LogoutCurrentSession`
- `create_tenant_admin` provisioning flow through application service

## Domain Model

- `User`
    - tenant-scoped user profile, locale/theme/timezone, last activity and login state
- `UserEmail`
    - primary/verified flags, email ownership and verification status

## Infrastructure / Persistence

- SQLAlchemy repositories store users and user emails
- token/session implementations use shared token infrastructure
- Redis-related settings exist in config, while auth services consume token/session backends

## Presentation / Entry Points

All current console auth routes live under `/api/console/auth`:

- `POST /request-otp`
- `POST /confirm-otp`
- `GET /me`
- `PATCH /me`
- `POST /logout`

## Auth Settings

- OTP code length
- OTP challenge TTL
- session TTL
- session cookie name
- in development mode, OTP code may be returned in response for easier local testing

## Dependencies On Other Modules

- uses `tenancy` host resolution rules and tenant availability checks
- uses `shared` request context, principals, token/time abstractions and auth dependencies

## Tests Covering This Module

- console auth endpoint tests
- authentication by session use case tests
- user service tests
- shared authentication dependency tests

## Related

- [HTTP API](../interfaces/http-api.md)
- [Configuration](../interfaces/configuration.md)
- [Domain models](../data/domain-models.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/identity/presentation/api/console_auth.py`
- `src/modules/identity/domain/entities.py`
- `src/modules/identity/application/auth/use_cases/`
- `src/config/feature/identity/auth_config.py`
