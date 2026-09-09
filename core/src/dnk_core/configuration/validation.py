"""Cross-group configuration validation with messages that never contain secrets."""

from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cryptography.fernet import Fernet

if TYPE_CHECKING:
    from dnk_core.config import CoreSettings


def _parse_url(value: str, setting: str):
    """Parse and validate a URL port without reflecting credentials in errors."""
    try:
        parsed = urlsplit(value)
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError()
    except ValueError:
        raise ValueError(f"{setting} must contain a valid URL and port.") from None
    return parsed


def validate_application(config: "CoreSettings") -> None:
    """Check origin, allowed hosts, encryption keys and timezone before startup."""
    if not config.secret_key.get_secret_value().strip():
        raise ValueError("CORE_SECRET_KEY must not be empty.")
    origin = _parse_url(config.effective_public_origin, "CORE_PUBLIC_ORIGIN")
    if (
        not origin.hostname
        or origin.scheme not in {"http", "https"}
        or origin.path
        or origin.query
        or origin.fragment
        or origin.username
        or origin.password
        or (not config.debug and origin.scheme != "https")
    ):
        raise ValueError(
            "CORE_PUBLIC_ORIGIN must be an origin, using HTTPS in production."
        )
    if not config.debug and (
        "*" in config.effective_allowed_hosts
        or origin.hostname not in config.effective_allowed_hosts
    ):
        raise ValueError(
            "CORE_ALLOWED_HOSTS must include the public hostname and exclude '*'."
        )
    if not config.mfa_encryption_key.get_secret_value() and not config.debug:
        raise ValueError("CORE_MFA_ENCRYPTION_KEY is required in production.")
    try:
        Fernet(config.effective_mfa_encryption_key)
    except (ValueError, TypeError):
        raise ValueError(
            "CORE_MFA_ENCRYPTION_KEY must be a valid Fernet key."
        ) from None
    try:
        ZoneInfo(config.time_zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(
            "CORE_TIME_ZONE must be an installed IANA time zone."
        ) from None


def validate_infrastructure(config: "CoreSettings") -> None:
    """Enforce production shared limits and mutually exclusive SMTP encryption modes."""
    if config.effective_redis_url:
        redis = _parse_url(config.effective_redis_url, "CORE_REDIS_URL")
        if redis.scheme not in {"redis", "rediss"} or not redis.hostname:
            raise ValueError(
                "CORE_REDIS_URL must be a valid redis:// or rediss:// URL."
            )
    elif not config.debug:
        raise ValueError("CORE_REDIS_URL or CORE_REDIS_HOST is required in production.")
    if config.effective_email_use_tls and config.email_use_ssl:
        raise ValueError(
            "CORE_EMAIL_USE_TLS and CORE_EMAIL_USE_SSL cannot both be true."
        )
    if not config.email_verify_certificate and not config.debug:
        raise ValueError(
            "CORE_EMAIL_VERIFY_CERTIFICATE=false requires CORE_DEBUG=true."
        )


def validate_authentication(config: "CoreSettings") -> None:
    """Require a usable passwordless path and complete explicitly enabled providers."""
    if (
        config.auth_password_mode in {"optional", "passwordless"}
        and not config.auth_email_code_enabled
    ):
        raise ValueError(
            "CORE_AUTH_EMAIL_CODE_ENABLED must be true for optional/passwordless mode."
        )
    if config.auth_passkey_signup_enabled and config.auth_signup_enabled:
        if not config.mfa_passkey_enrollment_enabled:
            raise ValueError(
                "CORE_AUTH_PASSKEY_SIGNUP_ENABLED requires CORE_MFA_PASSKEY_ENROLLMENT_ENABLED."
            )
        if not config.auth_passkey_login_enabled:
            raise ValueError(
                "CORE_AUTH_PASSKEY_SIGNUP_ENABLED requires CORE_AUTH_PASSKEY_LOGIN_ENABLED."
            )
    for name in ("google", "github", "telegram_login", "telegram_gateway"):
        config.validate_provider(name)


def validate_configuration(config: "CoreSettings") -> None:
    """Validate all configuration groups without opening an external connection."""
    validate_application(config)
    validate_infrastructure(config)
    validate_authentication(config)
