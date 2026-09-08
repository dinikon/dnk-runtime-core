from django import forms

from allauth.account.forms import RequestLoginCodeForm as AllauthRequestLoginCodeForm
from allauth.mfa.webauthn.forms import AddWebAuthnForm, LoginWebAuthnForm
from allauth.mfa.webauthn.internal import auth
from fido2.webauthn import UserVerificationRequirement


class EmailReauthenticationForm(forms.Form):
    code = forms.RegexField(
        regex=r"^[0-9]{6}$",
        label="Код из email",
        widget=forms.TextInput(
            attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}
        ),
    )


class RequestLoginCodeForm(AllauthRequestLoginCodeForm):
    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("email") and not cleaned.get("phone"):
            raise forms.ValidationError("Укажите email или телефон.")
        return cleaned

    def clean_phone(self):
        phone = super().clean_phone()
        if (
            phone
            and self._user
            and (not self._user.is_active or not self._user.phone_verified)
        ):
            self._user = None
        return phone


class AddPasskeyForm(AddWebAuthnForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Core always creates a discoverable passkey protected by PIN/biometrics.
        if "passwordless" in self.fields:
            self.fields["passwordless"].initial = True
            self.fields["passwordless"].disabled = True
            # allauth's JS reads `.checked`, so this must remain a checkbox.

    def clean(self):
        state = auth.get_state()
        if (
            not state
            or state.get("user_verification") != UserVerificationRequirement.REQUIRED
        ):
            raise forms.ValidationError("Начните добавление passkey заново.")
        return super().clean()


class LoginPasskeyForm(LoginWebAuthnForm):
    def clean_credential(self):
        state = auth.get_state()
        if (
            not state
            or state.get("user_verification") != UserVerificationRequirement.REQUIRED
        ):
            raise forms.ValidationError("Начните вход с passkey заново.")
        parsed = auth.parse_authentication_response(self.cleaned_data["credential"])
        if not parsed.response.authenticator_data.is_user_verified():
            raise forms.ValidationError(
                "Подтвердите личность с помощью PIN-кода или биометрии."
            )
        authenticator = super().clean_credential()
        if not authenticator.user.is_active:
            raise forms.ValidationError("Этот аккаунт неактивен.")
        return authenticator
