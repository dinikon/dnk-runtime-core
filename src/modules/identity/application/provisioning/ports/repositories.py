from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities import User


class UserRepositoryProtocol(Protocol):
    """Порт хранения пользователей для provisioning-сценариев."""

    async def add(self, user: User) -> None:
        """Добавляет пользователя и связанные email-адреса."""
        ...

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Возвращает пользователя по id или None."""
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

    async def exists_by_tenant_and_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> bool:
        """Проверяет существование email внутри tenant."""
        ...
