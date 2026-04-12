from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProvisionedTenantAdmin:
    """Результат provisioning tenant admin в identity-модуле."""

    user_id: UUID
    user_email_id: UUID
    user_status: str


class IdentityProvisioningServiceProtocol(Protocol):
    """Порт создания tenant admin пользователя во внешнем identity bounded context."""

    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> ProvisionedTenantAdmin:
        """Создает администратора tenant и возвращает его id/status metadata."""
        ...


__all__ = [
    "IdentityProvisioningServiceProtocol",
    "ProvisionedTenantAdmin",
]
