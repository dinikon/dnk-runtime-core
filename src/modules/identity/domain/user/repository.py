from __future__ import annotations

from typing import Protocol

from src.modules.identity.domain.user.entity import User
from src.modules.identity.domain.user.value_object import UserEmailIdVO, UserIdVO
from src.modules.shared import EntityIdVO


class UserRepositoryProtocol(Protocol):
    """Порт хранения и чтения пользователей identity."""

    async def add(self, user: User, *, tenant_id: EntityIdVO) -> None:
        """Добавляет пользователя и связанные email-адреса."""
        ...

    async def get_by_id(
        self, user_id: UserIdVO, *, tenant_id: EntityIdVO
    ) -> User | None:
        """Возвращает пользователя по id или None."""
        ...

    async def get_by_tenant_and_primary_email(
        self,
        tenant_id: EntityIdVO,
        email: str,
    ) -> User | None:
        """Возвращает пользователя tenant по primary email или None."""
        ...

    async def update_profile(self, user: User, *, tenant_id: EntityIdVO) -> None:
        """Сохраняет изменения профиля пользователя."""
        ...

    async def mark_email_verified(
        self, user_email_id: UserEmailIdVO, *, tenant_id: EntityIdVO
    ) -> None:
        """Помечает email пользователя как verified."""
        ...

    async def exists_by_tenant_and_email(
        self,
        tenant_id: EntityIdVO,
        email: str,
    ) -> bool:
        """Проверяет существование email внутри tenant."""
        ...


__all__ = ["UserRepositoryProtocol"]
