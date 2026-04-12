from __future__ import annotations

from uuid import UUID

from src.modules.identity.application.provisioning.services.user_service import (
    UserServiceProtocol,
)
from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
    ProvisionedTenantAdmin,
)


class IdentityProvisioningServiceAdapter(IdentityProvisioningServiceProtocol):
    """Адаптер tenancy-порта provisioning к identity UserService."""

    def __init__(self, user_service: UserServiceProtocol):
        """Инициализирует адаптер сервисом пользователей identity."""
        self._user_service = user_service

    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> ProvisionedTenantAdmin:
        """Создает tenant admin через identity и мапит результат в tenancy DTO."""
        result = await self._user_service.create_tenant_admin(
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        return ProvisionedTenantAdmin(
            user_id=result.user_id,
            user_email_id=result.user_email_id,
            user_status=result.user_status,
        )


__all__ = ["IdentityProvisioningServiceAdapter"]
