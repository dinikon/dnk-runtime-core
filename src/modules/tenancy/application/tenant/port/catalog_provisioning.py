from typing import Protocol
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogProvisioningPort(Protocol):
    """Порт onboarding для установки системной схемы Catalog."""

    async def initialize_defaults(
        self, tenant_id: TenantIdVO, actor_id: EntityIdVO
    ) -> None:
        """Создаёт Default в подготовленной tenant-схеме на общей транзакции."""
        ...
