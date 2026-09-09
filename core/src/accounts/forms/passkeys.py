"""WebAuthn input validation preserving allauth cryptographic checks."""

from django import forms
from allauth.mfa.webauthn.forms import (
    AddWebAuthnForm,
    LoginWebAuthnForm,
    SignupWebAuthnForm,
)
from allauth.mfa.webauthn.internal import auth
from fido2.webauthn import UserVerificationRequirement


class AddPasskeyForm(AddWebAuthnForm):
    """Require a user-verified challenge and a discoverable WebAuthn registration."""

    def __init__(self, *args, **kwargs):
        """Initialize the native component and apply CORE field or provider metadata."""
        super().__init__(*args, **kwargs)
        # Core always creates a discoverable passkey protected by PIN/biometrics.
        if "passwordless" in self.fields:
            self.fields["passwordless"].initial = True
            self.fields["passwordless"].disabled = True
            # allauth's JS reads `.checked`, so this must remain a checkbox.

    def clean(self):
        """Validate submitted input while retaining upstream allauth validation."""
        state = auth.get_state()
        if (
            not state
            or state.get("user_verification") != UserVerificationRequirement.REQUIRED
        ):
            raise forms.ValidationError("Начните добавление passkey заново.")
        try:
            return super().clean()
        except (ValueError, TypeError, KeyError) as exc:
            raise forms.ValidationError(
                "Некорректный ответ ключа доступа. Повторите попытку."
            ) from exc


class LoginPasskeyForm(LoginWebAuthnForm):
    """Validate user verification before native WebAuthn assertion verification."""

    def clean_credential(self):
        """Require the device owner flag before native signature and challenge checks."""
        state = auth.get_state()
        if (
            not state
            or state.get("user_verification") != UserVerificationRequirement.REQUIRED
        ):
            raise forms.ValidationError("Начните вход с passkey заново.")
        try:
            parsed = auth.parse_authentication_response(self.cleaned_data["credential"])
        except (ValueError, TypeError, KeyError) as exc:
            raise forms.ValidationError("Некорректный ответ ключа доступа.") from exc
        if not parsed.response.authenticator_data.is_user_verified():
            raise forms.ValidationError(
                "Подтвердите личность с помощью PIN-кода или биометрии."
            )
        authenticator = super().clean_credential()
        if not authenticator.user.is_active:
            raise forms.ValidationError("Этот аккаунт неактивен.")
        return authenticator


class SignupPasskeyForm(SignupWebAuthnForm):
    """Validate native passkey signup with mandatory user verification."""

    def clean(self):
        """Validate submitted input while retaining upstream allauth validation."""
        state = auth.get_state()
        if (
            not state
            or state.get("user_verification") != UserVerificationRequirement.REQUIRED
        ):
            raise forms.ValidationError("Начните создание ключа доступа заново.")
        try:
            return super().clean()
        except (ValueError, TypeError, KeyError) as exc:
            raise forms.ValidationError(
                "Некорректный ответ ключа доступа. Повторите попытку."
            ) from exc
