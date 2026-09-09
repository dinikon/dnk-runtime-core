"""Small extensions of allauth's OTP processes for multiple UUID contacts."""

from django.conf import settings
from allauth.account import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.internal.flows.login import perform_login, record_authentication
from allauth.account.internal.flows.login_by_code import LoginCodeVerificationProcess
from allauth.account.internal.flows.phone_verification import (
    ChangePhoneVerificationProcess,
)
from allauth.account.internal.flows.reauthentication import (
    raise_if_reauthentication_required,
)
from allauth.account.models import Login
from allauth.account.stages import LoginByCodeStage, LoginStageController

from .phone_proofs import LOGIN_PURPOSE, VERIFY_PURPOSE, bind_phone_proof


class PhoneLoginCodeProcess(LoginCodeVerificationProcess):
    """Retain allauth code generation while carrying contact identity through MFA."""

    @classmethod
    def initiate_for_contact(cls, request, contact):
        """Pin ownership before sending and persisting the native login stage."""
        login = Login(user=contact.user)
        login.state["stages"] = {"current": "login_by_code"}
        stage = LoginByCodeStage(LoginStageController(request, login), request, login)
        stage.state.update(
            cls.initial_state(user=contact.user, phone=contact.phone),
            initiated_by_user=True,
        )
        bind_phone_proof(stage.state, contact, LOGIN_PURPOSE)
        process = cls(stage)
        process.send()
        process.persist()
        return process

    def finish(self, redirect_url):
        """Record the validated contact so final login can recheck it after MFA."""
        user = self.user
        record_authentication(
            self.request,
            user,
            method="code",
            phone=self.state["phone"],
            phone_id=self.state["phone_id"],
            user_id=str(user.pk),
            purpose=LOGIN_PURPOSE,
        )
        get_adapter().set_phone_verified(user, self.state["phone"])
        return perform_login(self.request, Login(user=user, redirect_url=redirect_url))


class PhoneVerificationProcess(ChangePhoneVerificationProcess):
    """Use native delivery, expiration and attempts for one existing contact."""

    @property
    def can_resend(self):
        """Respect configured resend support and the native per-flow quota."""
        return not self.is_resend_quota_reached(
            app_settings.PHONE_VERIFICATION_MAX_RESEND_COUNT
        )

    def resend(self):
        """Consume a native resend attempt before delivering a fresh code."""
        self.record_resend()
        self.persist()
        self.send(skip_enumeration_sms=True)

    @classmethod
    def initiate_for_contact(cls, request, contact):
        """Bind a confirmation to its owner and UUID after recent authentication."""
        if settings.ACCOUNT_REAUTHENTICATION_REQUIRED:
            raise_if_reauthentication_required(request)
        state = cls.initial_state(user=request.user, phone=contact.phone)
        bind_phone_proof(state, contact, VERIFY_PURPOSE)
        process = cls(request, state)
        # Persist before delivery so an outage preserves the current challenge's
        # identity, replacing any older challenge in this browser session.
        process.persist()
        process.send()
        return process
