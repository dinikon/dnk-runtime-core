"""Phone normalization and atomic ownership changes for the CORE user model."""

from django.db import IntegrityError, transaction
from accounts.exceptions import PhoneConflictError
from accounts.models import User, phone_validator
from .capabilities import require_primary_login


def normalize_phone(phone):
    """Validate an unambiguous E.164 number and remove surrounding whitespace."""
    phone = phone.strip()
    phone_validator(phone)
    return phone


def set_phone(user, phone, verified):
    """Apply a phone change without leaking another account's ownership.

    The savepoint keeps a uniqueness violation from breaking an enclosing signup
    transaction. In-memory state is changed only after the database write succeeds.
    """
    phone = normalize_phone(phone) if phone else None
    try:
        with transaction.atomic():
            current = User.objects.select_for_update().get(pk=user.pk)
            if current.phone_verified and not (phone and verified):
                require_primary_login(current, exclude_phone=True)
            User.objects.filter(pk=user.pk).update(
                phone=phone, phone_verified=bool(phone and verified)
            )
    except IntegrityError:
        raise PhoneConflictError(
            "Этот номер недоступен для подключения.", code="phone_taken"
        ) from None
    user.phone = phone
    user.phone_verified = bool(phone and verified)
