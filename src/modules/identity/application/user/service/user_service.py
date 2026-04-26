from __future__ import annotations

from typing import Protocol

from src.modules.identity.application.user.dto import CreatedTenantAdmin
from src.modules.identity.domain.user import (
    User,
    UserEmailAlreadyExistsError,
    UserRepositoryProtocol,
)
from src.modules.shared import EntityIdVO

class UserServiceProtocol(Protocol):
    """Порт provisioning-сервиса пользователей identity."""

    async def create_tenant_admin(
        self,
        tenant_id: EntityIdVO,
        first_name: str,
        last_name: str,
        email: str,
    ) -> CreatedTenantAdmin:
        """Создает tenant admin пользователя с primary email."""
        ...


class UserService:
    """Application service provisioning пользователей identity."""

    def __init__(self, users_repository: UserRepositoryProtocol):
        """Инициализирует сервис repository-портом пользователей."""
        self._users_repository = users_repository

    async def create_tenant_admin(
        self,
        tenant_id: EntityIdVO,
        first_name: str,
        last_name: str,
        email: str,
    ) -> CreatedTenantAdmin:
        """Создает tenant admin и primary email после проверки уникальности email."""
        normalized_first_name = first_name.strip()
        normalized_last_name = last_name.strip()
        normalized_email = email.strip().lower()
        if await self._users_repository.exists_by_tenant_and_email(
            tenant_id=tenant_id,
            email=normalized_email,
        ):
            raise UserEmailAlreadyExistsError(normalized_email)

        user = User.create_tenant_admin(
            tenant_id=tenant_id,
            first_name=normalized_first_name,
            last_name=normalized_last_name,
        )
        primary_email = user.add_email(normalized_email, is_primary=True)
        await self._users_repository.add(user)
        return CreatedTenantAdmin(
            user_id=user.id.uuid,
            user_email_id=primary_email.id.uuid,
            user_status=user.status,
        )


__all__ = ["UserService", "UserServiceProtocol"]
