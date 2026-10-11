from uuid import UUID
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.currency.application.command.refresh_exchange_rates.handler import (
    RefreshExchangeRatesHandler,
)
from src.modules.currency.infrastructure.adapter.currency_catalog import (
    ReferenceDataExchangeRateCurrencyCatalog,
)
from src.modules.currency.infrastructure.nbu.source import NbuExchangeRateSource
from src.modules.currency.infrastructure.persistence.repository import (
    SqlAlchemyExchangeRateBookRepository,
)
from src.modules.currency.infrastructure.persistence.publication_lock import (
    PostgresExchangeRatePublicationLock,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.handler import (
    GetCurrencyValidationCatalogHandler,
)
from src.modules.reference_data.infrastructure.currency.persistence.validation_catalog_repository import (
    SqlAlchemyCurrencyValidationCatalogQueryRepository,
)
from src.modules.shared.domain.time.clock_port import ClockPort


def build_refresh_exchange_rates_handler(
    session: AsyncSession, client: httpx.AsyncClient, clock: ClockPort, tenant_id: UUID
) -> RefreshExchangeRatesHandler:
    """Собирает порты на общей ленивой сессии внешнего CLI/worker UoW."""
    return RefreshExchangeRatesHandler(
        NbuExchangeRateSource(client, clock),
        ReferenceDataExchangeRateCurrencyCatalog(
            GetCurrencyValidationCatalogHandler(
                SqlAlchemyCurrencyValidationCatalogQueryRepository(session)
            )
        ),
        SqlAlchemyExchangeRateBookRepository(session),
        PostgresExchangeRatePublicationLock(session, tenant_id),
        clock,
    )
