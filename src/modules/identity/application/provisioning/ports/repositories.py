from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities import User


class UserRepositoryProtocol(Protocol):
    async def add(self, user: User) -> None: ...
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def get_by_tenant_and_primary_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> User | None: ...
    async def mark_email_verified(self, user_email_id: UUID) -> None: ...
    async def exists_by_tenant_and_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> bool: ...
