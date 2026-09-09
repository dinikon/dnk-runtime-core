"""Revalidate OTP contact ownership under the caller's login transaction."""

from django.conf import settings
from allauth.account.models import EmailAddress
from accounts.models import User
from .phone_proofs import LOGIN_PURPOSE, proof_contact


def lock_code_owner(process):
    """Return the locked active owner, or None when ownership/features changed.

    Call inside the transaction that also verifies or resends the allauth code;
    releasing these locks before completing that action reopens the ownership race.
    """
    staged_user = process.user
    user = (
        User.objects.select_for_update().filter(pk=staged_user.pk).first()
        if staged_user
        else None
    )
    if not user or not user.is_active:
        return None
    phone, email = process.state.get("phone"), process.state.get("email")
    if phone:
        return (
            user
            if proof_contact(process.state, user.pk, LOGIN_PURPOSE, lock=True)
            else None
        )
    if email and settings.EMAIL_CODE_LOGIN_ENABLED:
        address = (
            EmailAddress.objects.select_for_update()
            .filter(user=user, email__iexact=email)
            .first()
        )
        return user if address else None
    return None
