# Configuration

Project configuration is assembled by `DnkConfig`, which combines multiple settings groups loaded from environment,
`.env` and `pyproject.toml`.

## Main Config Root

- `app_config`
    - `DnkConfig` composes database, redis, auth, deployment, control-plane and feature settings.
    - It is the single config object exposed as `dnk_config`.

## Database And SQLAlchemy

- Group: `config/infrastructure/__init__.py`
- Responsibilities:
    - DB connection parts: host, port, username, password, database
    - SQLAlchemy URI scheme
    - engine options, pool sizing, echo, connection extras
    - PostgreSQL URI building
- Critical for local run:
    - `DB_*`
    - `SQLALCHEMY_DATABASE_URI_SCHEME`
    - `SQLALCHEMY_ECHO`

## Identity Auth Config

- Group: `config/feature/identity/auth_config.py`
- Responsibilities:
    - OTP code length
    - OTP token TTL
    - session TTL
    - session cookie name
- Critical for behavior:
    - `AUTH.session_cookie_name`
    - `AUTH.otp_token_ttl_seconds`
    - `AUTH.session_ttl_seconds`

## Runtime Schema Config

- Group: `config/feature/runtime_schema/__init__.py`
- Responsibilities:
    - runtime schema name prefix
    - default seed module for bootstrap and diff
- Critical values:
    - `SCHEMA_PREFIX`
    - `DEFAULT_SEED_MODULE`

## Redis Config

- Group: `config/infrastructure/redis_config.py`
- Responsibilities:
    - Redis host, port, username, password, db, SSL mode
- Used by token/session related infrastructure paths

## Control Plane Config

- Group: `config/deploy/control_plane.py`
- Responsibilities:
    - bearer API key for control-plane protected routes
- Critical for tenancy admin route:
    - `CONTROL_PLANE_API_KEY`

## Deployment Config

- Group: `config/deploy/__init__.py`
- Responsibilities:
    - deployment environment flag such as `PRODUCTION` or `DEVELOPMENT`
- Current behavioral note:
    - identity OTP response may expose the OTP code only in development mode

## Related

- [HTTP API](http-api.md)
- [Management CLI](management-cli.md)
- [Identity module](../modules/identity.md)
- [Schema Registry module](../modules/schema-registry.md)

## Source Of Truth

- `src/config/app_config.py`
- `src/config/feature/identity/auth_config.py`
- `src/config/feature/runtime_schema/__init__.py`
- `src/config/infrastructure/__init__.py`
- `src/config/infrastructure/redis_config.py`
