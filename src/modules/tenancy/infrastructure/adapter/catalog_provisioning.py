from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.application.product_type.facade import (
    CatalogProvisioningFacade,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


class CatalogProvisioningAdapter:
    """Соединяет порт Tenancy с публичным фасадом Catalog на общем UoW."""

    def __init__(
        self,
        session: AsyncSession,
        naming: TenantSchemaNaming,
        facade: CatalogProvisioningFacade,
    ) -> None:
        """Принимает фасад, собранный на той же сессии, и привязку tenant-схемы."""
        self._session = session
        self._naming = naming
        self._facade = facade

    async def initialize_defaults(
        self, tenant_id: TenantIdVO, actor_id: EntityIdVO
    ) -> None:
        """Привязывает схему снаружи Catalog и вызывает его Application-контракт."""
        connection = await self._session.connection()
        await bind_tenant_schema(connection, tenant_id.uuid, self._naming)
        await self._facade.initialize_defaults(EntityIdVO(tenant_id.uuid), actor_id)
