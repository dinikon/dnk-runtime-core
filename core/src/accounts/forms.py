from django import forms

from allauth.account.forms import RequestLoginCodeForm as AllauthRequestLoginCodeForm
from allauth.account.forms import (
    LoginForm as AllauthLoginForm,
    SignupForm as AllauthSignupForm,
)
from allauth.socialaccount.forms import DisconnectForm as AllauthDisconnectForm
from allauth.mfa.webauthn.forms import (
    AddWebAuthnForm,
    LoginWebAuthnForm,
    SignupWebAuthnForm,
)
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


class LoginForm(AllauthLoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].label = "Email или имя пользователя"
        self.fields["login"].widget.attrs["placeholder"] = "Введите email или username"
        self.fields["password"].help_text = ""


class SignupForm(AllauthSignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.by_passkey:
            self.fields.pop("phone", None)


class RequestLoginCodeForm(AllauthRequestLoginCodeForm):
    def __init__(self, *args, channel=None, **kwargs):
        super().__init__(*args, **kwargs)
        if channel in {"email", "telegram"}:
            field = (
                "phone" if channel == "telegram" and "phone" in self.fields else "email"
            )
            self.fields = {field: self.fields[field]}
            self.fields[field].required = True

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
        try:
            return super().clean()
        except (ValueError, TypeError, KeyError) as exc:
            raise forms.ValidationError(
                "Некорректный ответ ключа доступа. Повторите попытку."
            ) from exc


class LoginPasskeyForm(LoginWebAuthnForm):
    def clean_credential(self):
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
    def clean(self):
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


class DisconnectForm(AllauthDisconnectForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account"].label = "Подключённый аккаунт"
        self.fields["account"].label_from_instance = (
            lambda account: f"{account.get_provider().name} · {account}"
        )

    def clean(self):
        # CORE has local passwordless methods that upstream does not consider.
        cleaned = forms.Form.clean(self)
        account = cleaned.get("account")
        if account:
            from django.conf import settings
            from allauth.account.models import EmailAddress
            from allauth.mfa.models import Authenticator
            from allauth.socialaccount.adapter import get_adapter

            user = self.request.user
            enabled = {
                "google": settings.GOOGLE_LOGIN_ENABLED,
                "github": settings.GITHUB_LOGIN_ENABLED,
                "telegram": settings.TELEGRAM_LOGIN_ENABLED,
            }
            other_social = (
                self.accounts.exclude(pk=account.pk)
                .filter(provider__in=[key for key, value in enabled.items() if value])
                .exists()
            )
            local = (
                user.has_usable_password()
                or EmailAddress.objects.filter(user=user, verified=True).exists()
                or (settings.PHONE_LOGIN_ENABLED and user.phone and user.phone_verified)
                or Authenticator.objects.filter(
                    user=user, type=Authenticator.Type.WEBAUTHN
                ).exists()
            )
            if not (local or other_social):
                raise forms.ValidationError("Сначала добавьте другой способ входа.")
            get_adapter().validate_disconnect(account, self.accounts)
        return cleaned
