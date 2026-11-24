from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.feed_builder.application.export_state.port.public_feed_tenant import (
    PublicFeedTenantResolverPort,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.application.tenant_domain.query.resolve_readable_tenant_by_host.handler import (
    ResolveReadableTenantByHostHandler,
)
from src.modules.tenancy.application.tenant_domain.query.resolve_readable_tenant_by_host.query import (
    ResolveReadableTenantByHostQuery,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    is_tenant_schema_bound,
)


class TenancyPublicFeedTenantResolver(PublicFeedTenantResolverPort):
    """Подключает разрешение хоста Tenancy к публичному экспорту."""

    def __init__(
        self,
        handler: ResolveReadableTenantByHostHandler,
        session: AsyncSession,
        naming: TenantSchemaNaming,
    ) -> None:
        """Получает обработчик Tenancy и сессию общего UoW запроса."""
        self._handler = handler
        self._session = session
        self._naming = naming

    async def resolve(self, host: str) -> UUID | None:
        """Подтверждает, что разрешённый хост совпадает с tenant-схемой запроса."""
        result = await self._handler.execute(ResolveReadableTenantByHostQuery(host))
        if result is None:
            return None
        connection = await self._session.connection()
        if not is_tenant_schema_bound(connection, result.tenant_id, self._naming):
            return None
        return result.tenant_id
