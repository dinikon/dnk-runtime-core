import logging
from uuid import UUID
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.modules.currency.application.command.refresh_exchange_rates.command import (
    RefreshExchangeRatesCommand,
)
from src.modules.currency.application.command.refresh_exchange_rates.dto import (
    RefreshExchangeRatesResultDTO,
)
from src.modules.currency.presentation.depends import (
    build_refresh_exchange_rates_handler,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock

from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate

logger = logging.getLogger(__name__)


async def refresh_exchange_rates(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    client: httpx.AsyncClient,
    tenant_id: UUID,
    naming: TenantSchemaNaming,
    clock: ClockPort | None = None,
) -> RefreshExchangeRatesResultDTO:
    """Запускает ручное обновление, возвращая результат только после успешного commit."""
    async with TenantGate(session_factory).hold(tenant_id) as connection:
        await bind_tenant_schema(connection, tenant_id, naming)
        async with UnitOfWork(
            async_sessionmaker(connection, expire_on_commit=False)
        ) as uow:
            result = await build_refresh_exchange_rates_handler(
                uow.session, client, clock or UtcClock(), tenant_id
            ).execute(RefreshExchangeRatesCommand())
    logger.info(
        "NBU exchange rates committed",
        extra={
            "event": "currency.refresh.committed",
            "tenant_id": str(tenant_id),
            "snapshot_id": str(result.snapshot_id),
            "quote_count": result.quote_count,
            "excluded_unknown_count": result.excluded_unknown_count,
            "excluded_metal_count": result.excluded_metal_count,
        },
    )
    return result
