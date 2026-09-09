"""CORE identities, verified phone contacts and UUID permission memberships."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from dnk_core.models import UUIDModel

phone_validator = RegexValidator(
    regex=r"^\+[1-9][0-9]{5,14}$",
    message="Введите номер в международном формате, например +380501234567.",
    code="invalid_phone",
)


class User(AbstractUser, UUIDModel):
    """Core identity, independent from users in the runtime's public schema."""

    middle_name = models.CharField("Отчество", max_length=150, blank=True, default="")
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        through="UserGroupMembership",
        related_name="user_set",
        related_query_name="user",
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        through="UserPermissionMembership",
        related_name="user_set",
        related_query_name="user",
        help_text="Specific permissions for this user.",
    )

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

        pass


class PhoneNumber(UUIDModel):
    """A user's contact; only verified numbers establish exclusive ownership."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="phone_numbers"
    )
    phone = models.CharField("Телефон", max_length=16, validators=[phone_validator])
    verified = models.BooleanField("Подтверждён", default=False)
    primary = models.BooleanField("Основной", default=False)
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)

    def __str__(self):
        """Display the contact without exposing internal identifiers."""
        return self.phone

    class Meta:
        """Protect ownership and primary selection across concurrent transactions."""

        ordering = ["-primary", "created_at", "pk"]
        verbose_name = "Телефон"
        verbose_name_plural = "Телефоны"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "phone"], name="accounts_user_phone_unique"
            ),
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(verified=True),
                name="accounts_verified_phone_unique",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(primary=True),
                name="accounts_primary_phone_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(primary=False) | models.Q(verified=True),
                name="accounts_primary_phone_verified",
            ),
            models.CheckConstraint(
                condition=~models.Q(phone=""),
                name="accounts_phone_not_empty",
            ),
        ]


class UserGroupMembership(UUIDModel):
    """Preserve Django group membership with an application-owned UUID key."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    group = models.ForeignKey("auth.Group", on_delete=models.CASCADE, related_name="+")

    class Meta:
        """Keep each group membership unique while supporting related-manager writes."""

        constraints = [
            models.UniqueConstraint(
                fields=["user", "group"], name="accounts_user_group_unique"
            )
        ]


class UserPermissionMembership(UUIDModel):
    """Preserve individual Django permissions with an application-owned UUID key."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    permission = models.ForeignKey(
        "auth.Permission", on_delete=models.CASCADE, related_name="+"
    )

    class Meta:
        """Prevent duplicate grants without changing Django's permission semantics."""

        constraints = [
            models.UniqueConstraint(
                fields=["user", "permission"], name="accounts_user_permission_unique"
            )
        ]
