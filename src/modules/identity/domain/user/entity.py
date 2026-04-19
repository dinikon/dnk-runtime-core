from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.modules.shared.domain.errors import DomainError


@dataclass(slots=True)
class UserEmail:
    """Доменная сущность email-адреса пользователя."""

    id: UUID
    user_id: UUID
    email: str
    is_primary: bool
    is_verified: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    def mark_verified(self) -> None:
        """Помечает email как verified, если он еще не подтвержден."""
        if self.is_verified:
            return
        now = datetime.now(UTC)
        self.is_verified = True
        self.updated_at = now


@dataclass(slots=True)
class User:
    """Доменная сущность пользователя identity."""

    id: UUID
    tenant_id: UUID
    status: str
    last_name: str
    first_name: str
    middle_name: str | None
    avatar: str | None
    interface_language: str
    interface_theme: str
    timezone: str
    last_login_at: datetime | None
    last_active_at: datetime
    last_login_ip: str | None
    initialized_at: datetime | None
    created_at: datetime
    updated_at: datetime
    emails: list[UserEmail] = field(default_factory=list)

    @classmethod
    def create_tenant_admin(
        cls,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
    ) -> "User":
        """Создает active tenant admin с profile defaults."""
        normalized_first_name = first_name.strip()
        normalized_last_name = last_name.strip()
        if not normalized_first_name:
            raise DomainError("User first name must not be empty.")
        if not normalized_last_name:
            raise DomainError("User last name must not be empty.")

        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            tenant_id=tenant_id,
            status="active",
            last_name=normalized_last_name,
            first_name=normalized_first_name,
            middle_name=None,
            avatar=None,
            interface_language="uk",
            interface_theme="system",
            timezone="Europe/Kyiv",
            last_login_at=None,
            last_active_at=now,
            last_login_ip=None,
            initialized_at=None,
            created_at=now,
            updated_at=now,
        )

    def add_email(
        self,
        email: str,
        *,
        is_primary: bool = False,
        is_verified: bool = False,
    ) -> UserEmail:
        """Добавляет email пользователю и запрещает второй primary email."""
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise DomainError("User email must not be empty.")

        if is_primary and any(existing.is_primary for existing in self.emails):
            raise DomainError("User already has a primary email.")

        now = datetime.now(UTC)
        user_email = UserEmail(
            id=uuid6.uuid7(),
            user_id=self.id,
            email=normalized_email,
            is_primary=is_primary,
            is_verified=is_verified,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        self.emails.append(user_email)
        self.updated_at = now
        return user_email

    def can_login(self) -> bool:
        """Показывает, разрешен ли login для пользователя."""
        return self.status == "active"

    def get_primary_email(self, email: str) -> UserEmail | None:
        """Возвращает primary email по адресу или None."""
        normalized_email = email.strip().lower()
        for existing in self.emails:
            if (
                existing.email == normalized_email
                and existing.is_primary
                and not existing.is_deleted
            ):
                return existing
        return None

    def mark_email_verified(self, user_email_id: UUID) -> None:
        """Помечает email пользователя как verified по id."""
        for email in self.emails:
            if email.id == user_email_id:
                email.mark_verified()
                self.updated_at = datetime.now(UTC)
                return
        raise DomainError(f"User email '{user_email_id}' was not found.")

    def update_profile(
        self,
        *,
        last_name: str,
        first_name: str,
        middle_name: str | None,
        interface_language: str,
        interface_theme: str,
        timezone: str,
    ) -> None:
        """Обновляет профиль пользователя и валидирует language/theme/timezone."""
        normalized_last_name = last_name.strip()
        normalized_first_name = first_name.strip()
        normalized_middle_name = (
            middle_name.strip() if middle_name is not None else None
        )
        normalized_interface_language = interface_language.strip().lower()
        if not isinstance(interface_theme, str):
            raise DomainError(
                "User interface theme must be one of: system, dark, light."
            )
        normalized_interface_theme = interface_theme.strip().lower()
        normalized_timezone = timezone.strip()

        if not normalized_last_name:
            raise DomainError("User last name must not be empty.")
        if not normalized_first_name:
            raise DomainError("User first name must not be empty.")
        if normalized_middle_name == "":
            normalized_middle_name = None

        if normalized_interface_language not in {"uk", "en"}:
            raise DomainError("User interface language must be one of: uk, en.")
        if normalized_interface_theme not in {"system", "dark", "light"}:
            raise DomainError(
                "User interface theme must be one of: system, dark, light."
            )
        if normalized_timezone not in {"Europe/Kyiv", "Europe/Warsaw"}:
            raise DomainError(
                "User timezone must be one of: Europe/Kyiv, Europe/Warsaw."
            )

        self.last_name = normalized_last_name
        self.first_name = normalized_first_name
        self.middle_name = normalized_middle_name
        self.interface_language = normalized_interface_language
        self.interface_theme = normalized_interface_theme
        self.timezone = normalized_timezone
        self.updated_at = datetime.now(UTC)


__all__ = ["User", "UserEmail"]
