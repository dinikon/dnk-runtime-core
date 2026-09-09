"""Scope phone enrollment to signup without blocking other login methods."""

from django.db import transaction
from django.conf import settings
from allauth.account.stages import (
    PhoneVerificationStage as AllauthPhoneVerificationStage,
)
from allauth.account.internal.flows.phone_verification import (
    PhoneVerificationStageProcess,
)
from allauth.core.internal.httpkit import headed_redirect_response
from accounts.models import User
from accounts.services.phone_proofs import VERIFY_PURPOSE, bind_phone_proof


class PhoneVerificationStage(AllauthPhoneVerificationStage):
    """Preserve first-signup verification while ignoring later pending contacts."""

    def handle(self):
        """Pin the signup contact before a code is issued by allauth."""
        if not settings.PHONE_LOGIN_ENABLED:
            return None, True
        user = self.login.user
        if user and user.last_login is not None and not self.login.signup:
            return None, True
        if not user:
            return super().handle()
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            if user.phone_numbers.filter(verified=True).exists():
                return None, True
            contact = user.phone_numbers.order_by("created_at", "pk").first()
            if contact is None:
                return None, True
            self.state.update(
                PhoneVerificationStageProcess.initial_state(
                    user=user, phone=contact.phone
                ),
                signup=self.login.signup,
            )
            process = PhoneVerificationStageProcess(self)
            bind_phone_proof(process.state, contact, VERIFY_PURPOSE)
            process.persist()
            process.send(skip_enumeration_sms=False)
        return headed_redirect_response("account_verify_phone"), True
