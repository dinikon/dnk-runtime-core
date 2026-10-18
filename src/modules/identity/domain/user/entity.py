from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import uuid6

from src.modules.identity.domain.user.value_object.user_email_id import UserEmailIdVO
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared.domain.domain_error import DomainError


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
