from __future__ import annotations
from src.modules.identity.application.user.command.create_tenant_admin.command import (
    CreateTenantAdminCommand,
)

from src.modules.identity.application.user.command.create_tenant_admin.handler import (
    CreateTenantAdminHandler,
)
from src.modules.shared import EntityIdVO
from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.application.ports.identity import ProvisionedTenantAdmin


class IdentityProvisioningServiceAdapter(IdentityProvisioningServiceProtocol):
    """Адаптер tenancy-порта provisioning к identity CreateTenantAdminHandler."""

    def __init__(self, user_service: CreateTenantAdminHandler) -> None:
        """Инициализирует адаптер сервисом пользователей identity."""
        self._user_service = user_service

    async def create_tenant_admin(
        self,
        tenant_id: EntityIdVO,
        first_name: str,
        last_name: str,
        email: str,
    ) -> ProvisionedTenantAdmin:
        """Создает tenant admin через identity и мапит результат в tenancy DTO."""
        result = await self._user_service.execute(
            CreateTenantAdminCommand(
                tenant_id=tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )
        )
        return ProvisionedTenantAdmin(
            user_id=result.user_id,
            user_email_id=result.user_email_id,
            user_status=result.user_status,
        )


__all__ = ["IdentityProvisioningServiceAdapter"]
