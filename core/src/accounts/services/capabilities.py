"""Effective authentication capabilities shared by endpoints and account policies.

Primary login methods are separate from reauthentication: a stored password may
still protect account changes when password login is disabled globally.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.socialaccount.models import SocialAccount


def password_login_enabled():
    """Return whether a password may start a new browser authentication flow."""
    return settings.AUTH_PASSWORD_MODE != "passwordless"


def enabled_providers():
    """List configured providers in the stable UI order without exposing secrets."""
    return [
        name
        for name in ("google", "github", "telegram")
        if getattr(settings, f"{name.upper()}_LOGIN_ENABLED")
    ]


def passkey_signup_enabled():
    """Require registration, enrollment and passkey signup to be enabled together."""
    return bool(
        settings.AUTH_SIGNUP_ENABLED
        and settings.MFA_PASSKEY_ENROLLMENT_ENABLED
        and settings.MFA_PASSKEY_SIGNUP_ENABLED
    )


def public_capabilities():
    """Return the public, JSON-safe feature contract consumed by Django and Nuxt."""
    return {
        "registrationEnabled": settings.AUTH_SIGNUP_ENABLED,
        "passwordLoginEnabled": password_login_enabled(),
        "emailCodeLoginEnabled": settings.EMAIL_CODE_LOGIN_ENABLED,
        "phoneCodeLoginEnabled": settings.PHONE_LOGIN_ENABLED,
        "passkeyLoginEnabled": settings.MFA_PASSKEY_LOGIN_ENABLED,
        "passkeySignupEnabled": passkey_signup_enabled(),
        "providers": enabled_providers(),
    }


def has_primary_login(
    user,
    *,
    exclude_social=None,
    exclude_passkey=None,
    exclude_email=None,
    exclude_phone=False,
):
    """Check remaining usable primary methods after a proposed account change.

    TOTP and recovery codes cannot start a new login and never count as fallback
    primary methods. Disabled providers and password reauthentication also do not.
    """
    if password_login_enabled() and user.has_usable_password():
        return True
    emails = EmailAddress.objects.filter(user=user, verified=True)
    if exclude_email is not None:
        emails = emails.exclude(pk=exclude_email)
    if settings.EMAIL_CODE_LOGIN_ENABLED and emails.exists():
        return True
    if (
        settings.PHONE_LOGIN_ENABLED
        and not exclude_phone
        and user.phone
        and user.phone_verified
    ):
        return True
    keys = Authenticator.objects.filter(user=user, type=Authenticator.Type.WEBAUTHN)
    if exclude_passkey is not None:
        keys = keys.exclude(pk=exclude_passkey)
    if settings.MFA_PASSKEY_LOGIN_ENABLED and keys.exists():
        return True
    socials = SocialAccount.objects.filter(user=user, provider__in=enabled_providers())
    if exclude_social is not None:
        socials = socials.exclude(pk=exclude_social)
    return socials.exists()


def require_primary_login(user, **exclusions):
    """Reject a change that would leave the account without a primary login."""
    if not has_primary_login(user, **exclusions):
        raise ValidationError("Сначала добавьте другой способ входа.")
