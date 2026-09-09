"""Translate supported CORE authentication policies into allauth settings."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnk_core.config import CoreSettings


def authentication_settings(config: "CoreSettings") -> dict:
    """Derive primary authentication and enrollment without removing stored MFA types."""
    phone_enabled = config.provider_enabled("telegram_gateway")
    login_methods = {"email"}
    signup_fields = ["username*", "email*"]
    if config.auth_password_mode != "passwordless":
        login_methods.add("username")
        suffix = "*" if config.auth_password_mode == "required" else ""
        signup_fields.extend(["password1" + suffix, "password2" + suffix])
    if phone_enabled:
        login_methods.add("phone")
        signup_fields.append("phone")
    return {
        "AUTH_PASSWORD_MODE": config.auth_password_mode,
        "AUTH_SIGNUP_ENABLED": config.auth_signup_enabled,
        "EMAIL_CODE_LOGIN_ENABLED": config.auth_email_code_enabled,
        "PHONE_LOGIN_ENABLED": phone_enabled,
        "TELEGRAM_GATEWAY_TOKEN": config.telegram_gateway_token.get_secret_value(),
        "TELEGRAM_GATEWAY_TIMEOUT": config.telegram_gateway_timeout,
        "ACCOUNT_LOGIN_METHODS": login_methods,
        "ACCOUNT_SIGNUP_FIELDS": signup_fields,
        "ACCOUNT_LOGIN_BY_CODE_ENABLED": config.auth_email_code_enabled
        or phone_enabled,
        "ACCOUNT_LOGIN_BY_CODE_TIMEOUT": config.auth_code_timeout,
        "ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS": config.auth_code_max_attempts,
        "ACCOUNT_LOGIN_BY_CODE_SUPPORTS_RESEND": config.auth_code_resend_enabled,
        "ACCOUNT_PHONE_VERIFICATION_TIMEOUT": config.auth_code_timeout,
        "ACCOUNT_PHONE_VERIFICATION_MAX_ATTEMPTS": config.auth_code_max_attempts,
        "ACCOUNT_PHONE_VERIFICATION_SUPPORTS_RESEND": config.auth_code_resend_enabled,
        "ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT": config.email_verification_timeout,
        "ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS": config.email_verification_max_attempts,
        "ACCOUNT_EMAIL_VERIFICATION_MAX_RESEND_COUNT": config.email_verification_max_resends,
        "ACCOUNT_REAUTHENTICATION_TIMEOUT": config.reauthentication_timeout,
        "EMAIL_REAUTHENTICATION_TIMEOUT": config.email_reauthentication_timeout,
        "EMAIL_REAUTHENTICATION_MAX_ATTEMPTS": config.email_reauthentication_max_attempts,
        "ACCOUNT_RATE_LIMITS": {
            "core_email_reauthenticate": (
                f"1/{config.email_reauthentication_resend_wait_seconds}s/user,"
                f"{config.email_reauthentication_max_per_hour}/h/user"
            )
        },
        "MFA_TOTP_ENROLLMENT_ENABLED": config.mfa_totp_enrollment_enabled,
        "MFA_PASSKEY_ENROLLMENT_ENABLED": config.mfa_passkey_enrollment_enabled,
        "MFA_PASSKEY_LOGIN_ENABLED": config.auth_passkey_login_enabled,
        "MFA_PASSKEY_SIGNUP_ENABLED": (
            config.auth_passkey_signup_enabled
            and config.auth_signup_enabled
            and config.mfa_passkey_enrollment_enabled
        ),
        "MFA_TOTP_ISSUER": config.mfa_totp_issuer,
    }


def social_settings(config: "CoreSettings") -> dict:
    """Create provider apps from enabled credentials while fixing OAuth security policy."""
    result = {}
    providers = {}
    for name in ("google", "github", "telegram_login"):
        key = name.upper()
        enabled = config.provider_enabled(name)
        result[
            f"{key}_ENABLED" if name == "telegram_login" else f"{key}_LOGIN_ENABLED"
        ] = enabled
        result[f"{key}_CLIENT_ID"] = getattr(config, f"{name}_client_id")
        result[f"{key}_CLIENT_SECRET"] = getattr(
            config, f"{name}_client_secret"
        ).get_secret_value()
        if not enabled:
            continue
        app = {
            "client_id": result[f"{key}_CLIENT_ID"],
            "secret": result[f"{key}_CLIENT_SECRET"],
            "key": "",
        }
        if name == "telegram_login":
            app.pop("key")
            app.update(
                {
                    "provider_id": "telegram",
                    "name": "Telegram",
                    "settings": {
                        "server_url": "https://oauth.telegram.org",
                        "token_auth_method": "client_secret_basic",
                        "scope": ["openid", "profile"],
                        "oauth_pkce_enabled": True,
                        "fetch_userinfo": False,
                    },
                }
            )
            providers["openid_connect"] = {"APPS": [app]}
        elif name == "google":
            providers[name] = {
                "APPS": [app],
                "SCOPE": ["profile", "email"],
                "AUTH_PARAMS": {"access_type": "online"},
                "OAUTH_PKCE_ENABLED": True,
            }
        else:
            providers[name] = {"APPS": [app], "SCOPE": ["user:email"]}
    result["SOCIALACCOUNT_PROVIDERS"] = providers
    return result
