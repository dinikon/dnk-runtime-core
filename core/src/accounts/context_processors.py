from django.conf import settings


def account_features(request):
    return {
        "site_name": "dNiko Alpha",
        "app_url": "/app/",
        "phone_login_enabled": settings.PHONE_LOGIN_ENABLED,
        "google_enabled": settings.GOOGLE_LOGIN_ENABLED,
        "github_enabled": settings.GITHUB_LOGIN_ENABLED,
        "telegram_login_enabled": settings.TELEGRAM_LOGIN_ENABLED,
        "passkey_signup_continue": bool(
            request.session.get("core_passkey_signup_next")
        ),
    }
