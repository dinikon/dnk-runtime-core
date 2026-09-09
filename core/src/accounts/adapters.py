import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.shortcuts import redirect

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.internal.flows.reauthentication import stash_and_reauthenticate
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.mfa.adapter import DefaultMFAAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import AuthProcess, Provider, ProviderAccount

from . import reauthentication
from .exceptions import PhoneConflictError
from .models import User, phone_validator
from .telegram import TelegramDeliveryError, TelegramGatewayClient

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    @transaction.atomic
    def save_user(self, request, user, form, commit=True):
        # allauth saves the user before assigning their optional phone. Keep both
        # writes atomic when another signup claims the number concurrently.
        return super().save_user(request, user, form, commit=commit)

    def clean_phone(self, phone):
        phone = phone.strip()
        phone_validator(phone)
        return phone

    def get_phone(self, user):
        return (user.phone, user.phone_verified) if user.phone else None

    def get_user_by_phone(self, phone):
        # Also used by allauth's ownership checks. The login form separately
        # excludes inactive accounts and numbers that have not been verified.
        return User.objects.filter(phone=phone).first()

    def set_phone(self, user, phone, verified):
        phone = self.clean_phone(phone) if phone else None
        try:
            with transaction.atomic():
                User.objects.filter(pk=user.pk).update(
                    phone=phone,
                    phone_verified=bool(phone and verified),
                )
        except IntegrityError:
            raise PhoneConflictError(
                "Этот номер недоступен для подключения.", code="phone_taken"
            ) from None
        user.phone = phone
        user.phone_verified = bool(phone and verified)

    def set_phone_verified(self, user, phone):
        # ChangePhoneVerificationProcess also calls this for a newly verified
        # replacement. The old number remains usable until verification succeeds.
        self.set_phone(user, phone, True)

    def send_verification_code_sms(self, user, phone, code, **kwargs):
        try:
            TelegramGatewayClient().send_verification_code(phone, code, ttl=300)
        except TelegramDeliveryError as exc:
            # The exception contains a fixed category, never provider response data.
            logger.warning("Telegram Gateway delivery failed: %s", exc)
            messages.error(
                self.request,
                "Не удалось обработать запрос на отправку кода. "
                "Повторите позже или выберите другой способ входа.",
            )
            target = (
                "account_change_phone"
                if self.request.user.is_authenticated
                else "account_request_login_code"
            )
            raise ImmediateHttpResponse(redirect(target)) from None

    def send_unknown_account_sms(self, phone, **kwargs):
        # Gateway accepts only numeric codes, not allauth's explanatory SMS.
        # Keep enumeration protection without charging for nonexistent accounts.
        return None

    def send_account_already_exists_sms(self, phone):
        return None


class MFAAdapter(DefaultMFAAdapter):
    """Encrypt allauth secrets at rest with a separate, stable Fernet key."""

    def encrypt(self, text):
        return (
            "fernet:"
            + Fernet(settings.MFA_ENCRYPTION_KEY).encrypt(text.encode()).decode()
        )

    def decrypt(self, encrypted_text):
        if not encrypted_text.startswith("fernet:"):
            raise ImproperlyConfigured(
                "Core MFA data must use its configured encryption key."
            )
        try:
            return (
                Fernet(settings.MFA_ENCRYPTION_KEY)
                .decrypt(encrypted_text.removeprefix("fernet:").encode())
                .decode()
            )
        except (InvalidToken, ValueError):
            raise ImproperlyConfigured(
                "Core MFA data cannot be decrypted with this key."
            ) from None

    def get_public_key_credential_rp_entity(self):
        result = super().get_public_key_credential_rp_entity()
        result["name"] = "dNiko Alpha"
        return result


class DisabledSocialProvider(Provider):
    """Display saved connections without enabling redirects or token login."""

    uses_apps = False
    account_class = ProviderAccount

    def __init__(self, request, provider):
        super().__init__(request)
        self.id = provider
        self.name = {"google": "Google", "github": "GitHub", "telegram": "Telegram"}[
            provider
        ]


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_provider(self, request, provider, client_id=None):
        enabled = {
            "google": settings.GOOGLE_LOGIN_ENABLED,
            "github": settings.GITHUB_LOGIN_ENABLED,
            "telegram": settings.TELEGRAM_LOGIN_ENABLED,
        }
        if provider in enabled and not enabled[provider]:
            return DisabledSocialProvider(request, provider)
        result = super().get_provider(request, provider, client_id=client_id)
        if getattr(result, "sub_id", None) == "telegram":
            from .oidc import TelegramProvider

            result = TelegramProvider(request, app=result.app)
        return result

    def is_auto_signup_allowed(self, request, sociallogin):
        if sociallogin.account.provider == "telegram":
            return False
        return super().is_auto_signup_allowed(request, sociallogin)

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)
        # OAuth may finish after the recent-auth window used to start a connect.
        # Native allauth skips this check for users with no local reauth method.
        if (
            sociallogin.state.get("process") == AuthProcess.CONNECT
            and reauthentication.uses_email_reauthentication(request.user)
            and not reauthentication.recently_authenticated(request)
        ):
            stash_and_reauthenticate(
                request,
                sociallogin.serialize(),
                "allauth.socialaccount.internal.flows.connect.resume_connect",
            )
            raise ImmediateHttpResponse(redirect("core_email_reauthenticate"))
