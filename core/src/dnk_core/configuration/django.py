"""Translate typed deployment settings into Django's public settings contract."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnk_core.config import CoreSettings


def application_settings(config: "CoreSettings") -> dict:
    """Project application settings and enforce the same-origin browser boundary."""
    result = {
        "SECRET_KEY": config.secret_key.get_secret_value(),
        "DEBUG": config.debug,
        "PUBLIC_ORIGIN": config.effective_public_origin,
        "ALLOWED_HOSTS": config.effective_allowed_hosts,
        "MFA_ENCRYPTION_KEY": config.effective_mfa_encryption_key,
        "ALLAUTH_TRUSTED_PROXY_COUNT": config.trusted_proxy_count,
        "SESSION_COOKIE_AGE": config.session_cookie_age,
        "ACCOUNT_SESSION_REMEMBER": config.session_remember,
        "SESSION_COOKIE_SECURE": not config.debug,
        "CSRF_COOKIE_SECURE": not config.debug,
        "CSRF_TRUSTED_ORIGINS": [config.effective_public_origin],
        "SECURE_SSL_REDIRECT": not config.debug,
        "SECURE_HSTS_SECONDS": 0 if config.debug else 31536000,
        "LANGUAGE_CODE": config.language_code,
        "TIME_ZONE": config.time_zone,
    }
    if config.trust_proxy:
        result["SECURE_PROXY_SSL_HEADER"] = ("HTTP_X_FORWARDED_PROTO", "https")
    return result


def infrastructure_settings(config: "CoreSettings", base_dir) -> dict:
    """Project isolated PostgreSQL/cache connections and the selected mail backend."""
    redis_url = config.effective_redis_url
    cache = {
        "BACKEND": (
            "django.core.cache.backends.redis.RedisCache"
            if redis_url
            else "django.core.cache.backends.locmem.LocMemCache"
        ),
        "LOCATION": redis_url or "dnk-core-development",
        "KEY_PREFIX": "dnk:core",
    }
    return {
        "DATABASES": {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": config.db_name,
                "USER": config.db_user,
                "PASSWORD": config.db_password.get_secret_value(),
                "HOST": config.db_host,
                "PORT": str(config.db_port),
                "OPTIONS": {"options": "-c search_path=core"},
            }
        },
        "REDIS_URL": redis_url,
        "CACHES": {"default": cache},
        "EMAIL_BACKEND": config.effective_email_backend,
        "EMAIL_HOST": config.email_host,
        "EMAIL_PORT": config.email_port,
        "EMAIL_HOST_USER": config.email_host_user,
        "EMAIL_HOST_PASSWORD": config.email_host_password.get_secret_value(),
        "EMAIL_USE_TLS": config.effective_email_use_tls,
        "EMAIL_USE_SSL": config.email_use_ssl,
        "EMAIL_VERIFY_CERTIFICATE": config.email_verify_certificate,
        "EMAIL_FILE_PATH": config.email_file_path or str(base_dir / "mail-outbox"),
        "EMAIL_TIMEOUT": config.email_timeout,
        "DEFAULT_FROM_EMAIL": config.default_from_email,
        "ACCOUNT_EMAIL_SUBJECT_PREFIX": config.email_subject_prefix,
        "ACCOUNT_EMAIL_NOTIFICATIONS": config.email_notifications,
    }
