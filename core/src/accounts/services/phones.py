"""Transactional phone ownership and primary selection for CORE accounts."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.exceptions import PhoneConflictError
from accounts.models import PhoneNumber, User, phone_validator


def normalize_phone(phone):
    """Validate an unambiguous E.164 number and remove surrounding whitespace."""
    phone = phone.strip()
    phone_validator(phone)
    return phone


def login_phones(user=None):
    """Return only contacts that may currently initiate phone authentication."""
    contacts = PhoneNumber.objects.filter(verified=True, user__is_active=True)
    if not settings.PHONE_LOGIN_ENABLED:
        return contacts.none()
    if settings.AUTH_PHONE_LOGIN_MODE == "primary_only":
        contacts = contacts.filter(primary=True)
    return contacts.filter(user=user) if user is not None else contacts


def verified_owner(phone):
    """Find exclusive ownership independently of login policy and account activity."""
    contact = (
        PhoneNumber.objects.select_related("user")
        .filter(phone=phone, verified=True)
        .first()
    )
    return contact.user if contact else None


def add_phone(user, phone):
    """Add an unverified contact without reserving another person's number."""
    phone = normalize_phone(phone)
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if user.phone_numbers.filter(phone=phone).exists():
            raise ValidationError(
                "Этот номер уже добавлен в ваш аккаунт.", code="duplicate_phone"
            )
        if user.phone_numbers.count() >= settings.AUTH_MAX_PHONE_NUMBERS:
            raise ValidationError(
                "Достигнут лимит номеров. Сначала удалите ненужный номер.",
                code="phone_limit",
            )
        return PhoneNumber.objects.create(user=user, phone=phone)


def confirm_phone(user, pk):
    """Verify an existing contact and select the first primary under an account lock."""
    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            contact = user.phone_numbers.select_for_update().get(pk=pk)
            if (
                PhoneNumber.objects.filter(phone=contact.phone, verified=True)
                .exclude(pk=pk)
                .exists()
            ):
                raise PhoneConflictError(
                    "Этот номер недоступен для подключения.", code="phone_taken"
                )
            contact.verified = True
            if not user.phone_numbers.filter(primary=True).exists():
                contact.primary = True
            contact.save(update_fields=["verified", "primary"])
            return contact
    except IntegrityError:
        raise PhoneConflictError(
            "Этот номер недоступен для подключения.", code="phone_taken"
        ) from None


def set_primary_phone(user, pk):
    """Select an owned verified phone without removing or reverifying other contacts."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        contact = user.phone_numbers.select_for_update().get(pk=pk)
        if not contact.verified:
            raise ValidationError("Сначала подтвердите номер.")
        user.phone_numbers.filter(primary=True).exclude(pk=pk).update(primary=False)
        contact.primary = True
        contact.save(update_fields=["primary"])
        return contact


def remove_phone(user, pk):
    """Remove one contact while preserving primary selection and an enabled login."""
    from .capabilities import require_primary_login

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        contact = user.phone_numbers.select_for_update().get(pk=pk)
        if (
            contact.primary
            and user.phone_numbers.filter(verified=True).exclude(pk=pk).exists()
        ):
            raise ValidationError(
                "Сначала назначьте другой подтверждённый номер основным."
            )
        if contact.verified:
            require_primary_login(user, exclude_phone=contact.pk)
        contact.delete()


def set_phone(user, phone, verified):
    """Adapt allauth's singular setter to an idempotent addition, never replacement.

    This hook is used during signup. Verification callbacks use confirm_phone on
    an existing UUID-bound contact instead of recreating missing records.
    """
    if not phone:
        return None
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        phone = normalize_phone(phone)
        contact = user.phone_numbers.filter(phone=phone).first()
        if contact is None:
            contact = add_phone(user, phone)
        return confirm_phone(user, contact.pk) if verified else contact
