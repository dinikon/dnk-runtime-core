from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import uuid6

from src.modules.identity.domain.user.value_object.user_email_id import UserEmailIdVO
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.currency import CurrencyVO


@dataclass(slots=True)
class UserEmail:
    """Доменная сущность email-адреса пользователя."""

    id: UserEmailIdVO
    user_id: UserIdVO
    email: str
    is_primary: bool
    is_verified: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UserIdVO,
        email: str,
        is_primary: bool = False,
        is_verified: bool = False,
    ) -> "UserEmail":
        """Создаёт принадлежащий пользователю email с новым идентификатором."""
        normalized = email.strip().lower()
        if not normalized:
            raise DomainError("User email must not be empty.")
        now = datetime.now(UTC)
        return cls.restore(
            id=UserEmailIdVO.from_value(uuid6.uuid7()),
            user_id=user_id,
            email=normalized,
            is_primary=is_primary,
            is_verified=is_verified,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UserEmailIdVO,
        user_id: UserIdVO,
        email: str,
        is_primary: bool,
        is_verified: bool,
        is_deleted: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> "UserEmail":
        """Восстанавливает сохранённый email без генерации новых ID и времени."""
        if not email:
            raise DomainError("User email must not be empty.")
        return cls(
            id=id,
            user_id=user_id,
            email=email,
            is_primary=is_primary,
            is_verified=is_verified,
            is_deleted=is_deleted,
            created_at=created_at,
            updated_at=updated_at,
        )

    def mark_verified(self) -> None:
        """Помечает email как verified, если он еще не подтвержден."""
        if self.is_verified:
            return
        now = datetime.now(UTC)
        self.is_verified = True
        self.updated_at = now


@dataclass(slots=True)
class User:
    """Корень агрегата пользователя, управляющий профилем и своими emails."""

    id: UserIdVO
    tenant_id: EntityIdVO
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
    role: str = "member"
    session_epoch: int = 0
    display_currency: CurrencyVO | None = None

    @classmethod
    def create(
        cls,
        tenant_id: EntityIdVO,
        first_name: str,
        last_name: str,
        role: str = "member",
    ) -> "User":
        """Создаёт пользователя с профилем и наследованием валюты Tenant."""
        normalized_first_name = first_name.strip()
        normalized_last_name = last_name.strip()
        # Bootstrap profiles may be incomplete; no name is inferred from email.
        now = datetime.now(UTC)
        return cls.restore(
            id=UserIdVO.from_value(uuid6.uuid7()),
            tenant_id=tenant_id,
            status="active",
            role=role,
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

    @classmethod
    def restore(
        cls,
        *,
        id: UserIdVO,
        tenant_id: EntityIdVO,
        status: str,
        last_name: str,
        first_name: str,
        middle_name: str | None,
        avatar: str | None,
        interface_language: str,
        interface_theme: str,
        timezone: str,
        last_login_at: datetime | None,
        last_active_at: datetime,
        last_login_ip: str | None,
        initialized_at: datetime | None,
        created_at: datetime,
        updated_at: datetime,
        emails: list[UserEmail] | None = None,
        role: str = "member",
        session_epoch: int = 0,
        display_currency: CurrencyVO | None = None,
    ) -> "User":
        """Восстанавливает агрегат, проверяя валюту, роль и принадлежность emails."""
        cls._ensure_display_currency(display_currency)
        if role not in {"admin", "member"} or session_epoch < 0:
            raise DomainError("Invalid user role or session epoch.")
        restored_emails = list(emails or [])
        if any(email.user_id != id for email in restored_emails):
            raise DomainError("User email belongs to another user.")
        if (
            sum(email.is_primary and not email.is_deleted for email in restored_emails)
            > 1
        ):
            raise DomainError("User already has a primary email.")
        return cls(
            id=id,
            tenant_id=tenant_id,
            status=status,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            avatar=avatar,
            interface_language=interface_language,
            interface_theme=interface_theme,
            timezone=timezone,
            last_login_at=last_login_at,
            last_active_at=last_active_at,
            last_login_ip=last_login_ip,
            initialized_at=initialized_at,
            created_at=created_at,
            updated_at=updated_at,
            emails=restored_emails,
            role=role,
            session_epoch=session_epoch,
            display_currency=display_currency,
        )

    @classmethod
    def create_tenant_admin(
        cls, tenant_id: EntityIdVO, first_name: str, last_name: str
    ) -> "User":
        """Создаёт администратора с прежними bootstrap-настройками профиля."""
        return cls.create(tenant_id, first_name, last_name, role="admin")

    @staticmethod
    def _ensure_display_currency(currency: CurrencyVO | None) -> None:
        """Допускает нормализованную валюту либо наследование настроек Tenant."""
        if currency is not None and not isinstance(currency, CurrencyVO):
            raise DomainError("User display currency must be CurrencyVO or None.")

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

        user_email = UserEmail.create(
            user_id=self.id,
            email=normalized_email,
            is_primary=is_primary,
            is_verified=is_verified,
        )
        now = user_email.created_at
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

    def mark_email_verified(self, user_email_id: UserEmailIdVO) -> None:
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
        display_currency: CurrencyVO | None = None,
        display_currency_provided: bool = False,
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

        if display_currency_provided:
            self._ensure_display_currency(display_currency)

        self.last_name = normalized_last_name
        self.first_name = normalized_first_name
        self.middle_name = normalized_middle_name
        self.interface_language = normalized_interface_language
        self.interface_theme = normalized_interface_theme
        self.timezone = normalized_timezone
        if display_currency_provided:
            self.display_currency = display_currency
        self.updated_at = datetime.now(UTC)


__all__ = ["User", "UserEmail"]
