from src.modules.tenancy.application.tenant.command.activate_tenant.command import (
    ActivateTenantCommand,
)
from src.modules.tenancy.application.ports.files import TenantStorageProtocol
from src.modules.tenancy.domain.tenant.repository import TenantRepositoryProtocol
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.domain.tenant.error import TenantCannotActivateError


class ActivateTenantHandler:
    """Координирует проверку хранилища и доменную активацию tenant."""

    def __init__(
        self, repository: TenantRepositoryProtocol, storage: TenantStorageProtocol
    ) -> None:
        """Принимает репозиторий tenant и межмодульный порт хранилища."""
        self._repository, self._storage = repository, storage

    async def execute(self, command: ActivateTenantCommand) -> None:
        """Активирует существующий tenant, оставляя commit внешней сборке."""
        tenant = await self._repository.get_by_id(
            TenantIdVO.from_value(command.tenant_id)
        )
        if tenant is None:
            raise TenantCannotActivateError("Tenant does not exist.")
        tenant.activate(storage_ready=await self._storage.is_ready(command.tenant_id))
        await self._repository.save(tenant)
