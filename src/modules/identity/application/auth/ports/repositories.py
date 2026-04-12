from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities import User


class AuthUserRepositoryPort(Protocol):
    """Порт чтения/обновления пользователей для auth use cases."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Возвращает пользователя по id или None."""
        ...

    async def update_profile(self, user: User) -> None:
        """Сохраняет изменения профиля пользователя."""
        ...

    async def get_by_tenant_and_primary_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> User | None:
        """Возвращает пользователя tenant по primary email или None."""
        ...

    async def mark_email_verified(self, user_email_id: UUID) -> None:
        """Помечает email пользователя как verified."""
        ...
