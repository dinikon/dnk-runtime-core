import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^\+[1-9][0-9]{5,14}$",
    message="Введите номер в международном формате, например +380501234567.",
    code="invalid_phone",
)


class User(AbstractUser):
    """Core identity, independent from users in the runtime's public schema."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    middle_name = models.CharField("Отчество", max_length=150, blank=True, default="")
    phone = models.CharField(
        "Телефон",
        max_length=16,
        null=True,
        blank=True,
        unique=True,
        validators=[phone_validator],
    )
    phone_verified = models.BooleanField("Телефон подтвержден", default=False)

    def get_full_name(self):
        """Return the display name in surname, given name, patronymic order."""
        return " ".join(
            part.strip()
            for part in (self.last_name, self.first_name, self.middle_name)
            if part.strip()
        )

    @property
    def display_name(self):
        """Present existing nameless accounts without exposing an internal username."""
        return self.get_full_name() or self.email or "Ваш аккаунт"

    @property
    def initials(self):
        """Use name initials, falling back to email for existing incomplete profiles."""
        parts = [
            part.strip() for part in (self.last_name, self.first_name) if part.strip()
        ]
        return (
            "".join(part[0] for part in parts).upper() or self.display_name[:2].upper()
        )

    class Meta(AbstractUser.Meta):
        """Keep persisted identity constraints independent of authentication switches."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone_verified=False)
                | models.Q(phone__isnull=False),
                name="accounts_verified_phone_present",
            ),
            models.CheckConstraint(
                condition=~models.Q(phone=""),
                name="accounts_phone_not_empty",
            ),
        ]
