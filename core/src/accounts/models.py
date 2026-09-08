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
    phone = models.CharField(
        "Телефон",
        max_length=16,
        null=True,
        blank=True,
        unique=True,
        validators=[phone_validator],
    )
    phone_verified = models.BooleanField("Телефон подтвержден", default=False)

    class Meta(AbstractUser.Meta):
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
