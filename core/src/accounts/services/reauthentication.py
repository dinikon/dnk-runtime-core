"""Email confirmation for social-only accounts lacking a local reauth method."""

import secrets
import time

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac

from allauth.account.authentication import get_authentication_records
from allauth.account.models import EmailAddress
from allauth.mfa.utils import is_mfa_enabled

STATE_KEY = "core_email_reauthentication"


def uses_email_reauthentication(user):
    """Choose email reauthentication only without usable password or enrolled MFA."""
    return (
        user.is_authenticated
        and not user.has_usable_password()
        and not is_mfa_enabled(user)
    )


def recently_authenticated(request):
    """Check the age of the most recent native authentication record."""
    records = get_authentication_records(request)
    return (
        bool(records)
        and 0
        <= time.time() - records[-1]["at"]
        < settings.ACCOUNT_REAUTHENTICATION_TIMEOUT
    )


def verified_email(user):
    """Choose a verified email, preferring the current primary address."""
    return (
        EmailAddress.objects.filter(user=user, verified=True)
        .order_by("-primary", "pk")
        .first()
    )


def code_digest(user_id, email, nonce, code):
    """Bind the proof digest to the user, verified address and random challenge nonce."""
    return salted_hmac(
        "core-email-reauthentication",
        f"{user_id}:{email}:{nonce}:{code}",
    ).hexdigest()


def new_state(user, email, code):
    """Create a short-lived hashed proof state without retaining the plaintext code."""
    nonce = secrets.token_urlsafe(24)
    return {
        "user_id": str(user.pk),
        "email": email,
        "nonce": nonce,
        "digest": code_digest(str(user.pk), email, nonce, code),
        "at": time.time(),
        "attempts": 0,
    }


def get_state(request):
    """Discard expired, exhausted or reassigned email proof state."""
    state = request.session.get(STATE_KEY)
    if state and (
        state["user_id"] != str(request.user.pk)
        or not 0 <= time.time() - state["at"] <= settings.EMAIL_REAUTHENTICATION_TIMEOUT
        or state["attempts"] >= settings.EMAIL_REAUTHENTICATION_MAX_ATTEMPTS
        or not EmailAddress.objects.filter(
            user=request.user,
            email=state["email"],
            verified=True,
        ).exists()
    ):
        request.session.pop(STATE_KEY, None)
        return None
    return state


def check_code(request, code):
    """Consume attempts and erase successful or exhausted email proof challenges."""
    state = get_state(request)
    if not state:
        return False
    state["attempts"] += 1
    valid = constant_time_compare(
        state["digest"],
        code_digest(state["user_id"], state["email"], state["nonce"], code),
    )
    if valid or state["attempts"] >= settings.EMAIL_REAUTHENTICATION_MAX_ATTEMPTS:
        request.session.pop(STATE_KEY, None)
    else:
        request.session[STATE_KEY] = state
    return valid
