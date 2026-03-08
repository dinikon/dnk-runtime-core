from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.identity.application.provisioning.ports.repositories import (
    UserRepositoryProtocol,
)
from src.modules.identity.domain.entities import User
from src.modules.identity.domain.errors import UserEmailAlreadyExistsError


@dataclass(frozen=True, slots=True)
class CreatedTenantAdmin:
    user_id: UUID
    user_email_id: UUID
    user_status: str


class UserServiceProtocol(Protocol):
    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> CreatedTenantAdmin: ...


class UserService:
    def __init__(self, users_repository: UserRepositoryProtocol):
        self._users_repository = users_repository

    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> CreatedTenantAdmin:
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
            user_id=user.id,
            user_email_id=primary_email.id,
            user_status=user.status,
        )
