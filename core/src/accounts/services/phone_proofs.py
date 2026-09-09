"""Bind native allauth proofs to stable contacts and their intended operation."""

from django.core.exceptions import ValidationError
from uuid import UUID
from allauth.account.authentication import get_authentication_records
from accounts.models import PhoneNumber
from .phones import login_phones

LOGIN_PURPOSE = "phone_login"
VERIFY_PURPOSE = "phone_verification"


def bind_phone_proof(state, contact, purpose):
    """Add JSON-safe contact identity without altering allauth's OTP state."""
    state.update(
        phone_id=str(contact.pk),
        user_id=str(contact.user_id),
        phone=contact.phone,
        purpose=purpose,
    )


def proof_contact(state, user_id, purpose, *, lock=False):
    """Reject old, removed, reassigned or currently disabled contact proofs."""
    try:
        user_id = UUID(str(user_id))
    except (ValueError, TypeError):
        return None
    if (
        not state
        or state.get("purpose") != purpose
        or state.get("user_id") != str(user_id)
        or not state.get("phone_id")
    ):
        return None
    contacts = login_phones() if purpose == LOGIN_PURPOSE else PhoneNumber.objects.all()
    if lock:
        contacts = contacts.select_for_update(of=("self",))
    try:
        return contacts.filter(
            pk=state["phone_id"], user_id=user_id, phone=state.get("phone")
        ).first()
    except (ValidationError, ValueError, TypeError):
        return None


def latest_phone_login(request):
    """Find the initiating phone proof, ignoring later MFA and reauthentication."""
    for record in reversed(get_authentication_records(request)):
        if record.get("reauthenticated"):
            continue
        method = record.get("method")
        if method in {"password", "socialaccount"} or (
            method == "mfa" and record.get("passwordless")
        ):
            return None
        if method == "code":
            return record if record.get("phone") else None
    return None
