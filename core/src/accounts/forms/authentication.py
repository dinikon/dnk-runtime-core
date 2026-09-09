"""Registration and primary authentication input validation."""

from django import forms
from django.conf import settings
from .profile import ProfileFields
from allauth.socialaccount.forms import SignupForm as AllauthSocialSignupForm
from accounts.services.capabilities import password_login_enabled
from allauth.account.forms import RequestLoginCodeForm as AllauthRequestLoginCodeForm
from allauth.account.forms import (
    LoginForm as AllauthLoginForm,
    SignupForm as AllauthSignupForm,
)


class LoginForm(AllauthLoginForm):
    """Adapt the primary form to password policy without changing reauthentication."""

    def __init__(self, *args, **kwargs):
        """Render only email for passwordless login and retain ordinary labels otherwise."""
        super().__init__(*args, **kwargs)
        if password_login_enabled():
            usernames = "username" in settings.ACCOUNT_LOGIN_METHODS
            self.fields["login"].label = (
                "Email или имя пользователя" if usernames else "Email"
            )
            self.fields["login"].widget.attrs["placeholder"] = (
                "Введите email или username" if usernames else "you@example.com"
            )
            if "password" in self.fields:
                self.fields["password"].help_text = ""
        else:
            self.fields.pop("password", None)
            self.fields["login"] = forms.EmailField(
                label="Email",
                widget=forms.EmailInput(
                    attrs={"autocomplete": "email", "placeholder": "you@example.com"}
                ),
            )

    def clean(self):
        """Reject stale password submissions before authentication or delivery occurs."""
        if not password_login_enabled() and self.data.get("password"):
            raise forms.ValidationError(
                "Вход по паролю отключён. Запросите код из email."
            )
        return super().clean()

    def _login_by_code(self, request, redirect_url, credentials):
        """Carry the remember choice through the code stage just as password login does."""
        response = super()._login_by_code(request, redirect_url, credentials)
        if settings.ACCOUNT_SESSION_REMEMBER is None:
            remember = self.cleaned_data.get("remember", False)
            request.session.set_expiry(settings.SESSION_COOKIE_AGE if remember else 0)
        return response

    def _clean_without_password(self, email, phone):
        """Use CORE's guarded OTP form instead of upstream's unconfigured form class."""
        if not settings.EMAIL_CODE_LOGIN_ENABLED:
            raise forms.ValidationError("Вход по коду из email отключён.")
        form = RequestLoginCodeForm({"email": email or ""}, channel="email")
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    self.add_error("login", error)
        else:
            self.user = form._user
        return self.cleaned_data

    def _clean_with_password(self, credentials):
        """Keep telephone login on the UUID-bound OTP path, including direct POSTs."""
        if credentials.get("phone"):
            raise forms.ValidationError(
                "Для входа по телефону запросите код в Telegram."
            )
        return super()._clean_with_password(credentials)


class SignupForm(ProfileFields, AllauthSignupForm):
    """Retain allauth signup behavior and omit the optional phone from passkey signup."""

    def __init__(self, *args, **kwargs):
        """Initialize the native component and apply CORE field or provider metadata."""
        super().__init__(*args, **kwargs)
        if self.by_passkey:
            self.fields.pop("phone", None)


class SocialSignupForm(ProfileFields, AllauthSocialSignupForm):
    """Complete provider-prefilled names through native allauth social registration."""


class RequestLoginCodeForm(AllauthRequestLoginCodeForm):
    """Validate explicit delivery channels and prevent invalid phone login targets."""

    def __init__(self, *args, channel=None, **kwargs):
        """Initialize the native component and apply CORE field or provider metadata."""
        super().__init__(*args, **kwargs)
        self.channel = channel
        if channel in {"email", "telegram"}:
            field = "phone" if channel == "telegram" else "email"
            self.fields = {field: self.fields[field]} if field in self.fields else {}
            if field in self.fields:
                self.fields[field].required = True

    def clean(self):
        """Validate enabled delivery channels before allauth can issue any code."""
        if (
            (self.channel == "email" or self.data.get("email"))
            and not settings.EMAIL_CODE_LOGIN_ENABLED
            or (self.channel == "telegram" or self.data.get("phone"))
            and not settings.PHONE_LOGIN_ENABLED
            or self.channel not in {None, "email", "telegram"}
        ):
            raise forms.ValidationError("Этот способ входа отключён. Выберите другой.")
        cleaned = super().clean()
        if not cleaned.get("email") and not cleaned.get("phone"):
            raise forms.ValidationError("Укажите email или телефон.")
        return cleaned

    def clean_phone(self):
        """Exclude inactive users and unverified phone numbers from code login."""
        from accounts.services.phones import login_phones

        phone = super().clean_phone()
        if phone:
            self.phone_contact = (
                login_phones().select_related("user").filter(phone=phone).first()
            )
            self._user = self.phone_contact.user if self.phone_contact else None
        return phone
