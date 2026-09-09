"""Bridge allauth account hooks to CORE contact and delivery services."""

import logging
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from accounts.models import User
from accounts.services import phones
from accounts.services.capabilities import has_primary_login
from accounts.integrations.telegram_gateway import (
    TelegramDeliveryError,
    TelegramGatewayClient,
)

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    """Translate allauth account hooks into CORE account policies and services."""

    @transaction.atomic
    def save_user(self, request, user, form, commit=True):
        # allauth saves the user before assigning their optional phone. Keep both
        # writes atomic when another signup claims the number concurrently.
        """Keep user creation and optional phone assignment in one transaction."""
        return super().save_user(request, user, form, commit=commit)

    def login(self, request, user):
        """Apply the configured session lifetime to every completed login method."""
        result = super().login(request, user)
        remember = settings.ACCOUNT_SESSION_REMEMBER
        if remember is not None:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE if remember else 0)
        return result

    def get_login_stages(self):
        """Retain the passkey stage so disabling signup cannot bypass its proof.

        Allauth normally removes this stage when the feature flag changes. A
        signup already waiting for email verification must still stop before
        authentication, then the guarded passkey endpoint aborts the old flow.
        """
        stages = super().get_login_stages()
        passkey_stage = "allauth.mfa.webauthn.stages.PasskeySignupStage"
        if passkey_stage not in stages:
            stages.append(passkey_stage)
        return stages

    def is_open_for_signup(self, request):
        """Apply the registration switch to normal and social allauth signup."""
        return settings.AUTH_SIGNUP_ENABLED

    def can_delete_email(self, email_address):
        """Preserve upstream contact rules and the last enabled primary method."""
        return super().can_delete_email(email_address) and (
            not email_address.pk
            or has_primary_login(email_address.user, exclude_email=email_address.pk)
        )

    def clean_phone(self, phone):
        """Normalize the phone using the shared ownership service."""
        return phones.normalize_phone(phone)

    def get_phone(self, user):
        """Expose the stored normalized phone and its verification status to allauth."""
        return (user.phone, user.phone_verified) if user.phone else None

    def get_user_by_phone(self, phone):
        # Also used by allauth's ownership checks. The login form separately
        # excludes inactive accounts and numbers that have not been verified.
        """Find a phone owner without weakening allauth ownership checks."""
        return User.objects.filter(phone=phone).first()

    def set_phone(self, user, phone, verified):
        """Keep allauth phone writes behind the atomic ownership service."""
        phones.set_phone(user, phone, verified)

    def set_phone_verified(self, user, phone):
        # ChangePhoneVerificationProcess also calls this for a newly verified
        # replacement. The old number remains usable until verification succeeds.
        """Commit a replacement phone only after its verification succeeds."""
        self.set_phone(user, phone, True)

    def send_verification_code_sms(self, user, phone, code, **kwargs):
        """Send an allauth code through Telegram and present a safe delivery error."""
        try:
            TelegramGatewayClient().send_verification_code(
                phone, code, ttl=settings.ACCOUNT_PHONE_VERIFICATION_TIMEOUT
            )
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
        """Preserve enumeration protection without sending to unknown phone numbers."""
        return None

    def send_account_already_exists_sms(self, phone):
        """Avoid Telegram delivery for explanatory account-exists messages."""
        return None
