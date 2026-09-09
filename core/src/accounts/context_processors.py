from django.conf import settings

from accounts.services.capabilities import public_capabilities
from accounts.presentation.navigation import show_admin_link


def account_features(request):
    """Expose the shared authentication policy without exposing provider secrets."""
    capabilities = public_capabilities()
    providers = capabilities["providers"]
    return {
        "site_name": "dNiko Alpha",
        "app_url": "/app/",
        "show_admin_link": show_admin_link(request.user),
        "registration_enabled": capabilities["registrationEnabled"],
        "password_login_enabled": capabilities["passwordLoginEnabled"],
        "email_code_login_enabled": capabilities["emailCodeLoginEnabled"],
        "phone_login_enabled": capabilities["phoneCodeLoginEnabled"],
        "passkey_login_enabled": capabilities["passkeyLoginEnabled"],
        "passkey_signup_enabled": capabilities["passkeySignupEnabled"],
        "available_providers": providers,
        "google_enabled": "google" in providers,
        "github_enabled": "github" in providers,
        "telegram_login_enabled": "telegram" in providers,
        "mfa_totp_enrollment_enabled": settings.MFA_TOTP_ENROLLMENT_ENABLED,
        "mfa_passkey_enrollment_enabled": settings.MFA_PASSKEY_ENROLLMENT_ENABLED,
        "passkey_signup_continue": bool(
            request.session.get("core_passkey_signup_next")
        ),
    }
