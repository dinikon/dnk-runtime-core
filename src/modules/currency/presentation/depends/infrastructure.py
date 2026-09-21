from dataclasses import dataclass
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from src.config import dnk_config
from src.modules.currency.application.exchange_rate.reader import RateReader
from src.modules.currency.application.provider.catalog import RateSourceCatalog
from src.modules.currency.application.provider.registry import (
    ExchangeRateProviderRegistry,
)
from src.modules.currency.infrastructure.persistence.directory.repository import (
    SqlCurrencyDirectory,
)
from src.modules.currency.infrastructure.persistence.enabled_currency.repository import (
    SqlEnabledCurrencyRepository,
)
from src.modules.currency.infrastructure.persistence.functional_currency.repository import (
    SqlFunctionalCurrencyRepository,
)
from src.modules.currency.infrastructure.persistence.manual_rate.repository import (
    SqlManualRateRepository,
)
from src.modules.currency.infrastructure.persistence.policy.repository import (
    SqlCurrencyPolicyRepository,
)
from src.modules.currency.infrastructure.persistence.provider_rate.repository import (
    SqlProviderRateRepository,
)
from src.modules.currency.infrastructure.providers.nbu.adapter import NbuAdapter
from src.modules.currency.infrastructure.providers.nbu.client import NbuClient
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


@dataclass(slots=True)
class CurrencyRepositories:
    """Repositories sharing one session; each tenant is passed to each operation."""

    directory: SqlCurrencyDirectory
    enabled: SqlEnabledCurrencyRepository
    policies: SqlCurrencyPolicyRepository
    periods: SqlFunctionalCurrencyRepository
    manual: SqlManualRateRepository
    provider: SqlProviderRateRepository
    rates: RateReader


def build_repositories(
    session: AsyncSession, naming: TenantSchemaNaming | None = None
) -> CurrencyRepositories:
    """Share the provided UoW session across every tenant and global read."""
    naming = naming or TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    manual, provider = SqlManualRateRepository(
        session, naming
    ), SqlProviderRateRepository(session, naming)
    return CurrencyRepositories(
        SqlCurrencyDirectory(session),
        SqlEnabledCurrencyRepository(session, naming),
        SqlCurrencyPolicyRepository(session, naming),
        SqlFunctionalCurrencyRepository(session, naming),
        manual,
        provider,
        RateReader(manual, provider),
    )


def get_currency_repositories(uow: UoWDep) -> CurrencyRepositories:
    """Compose currency repositories for the current unit of work."""
    return build_repositories(uow.session)


CurrencyRepositoriesDep = Annotated[
    CurrencyRepositories, Depends(get_currency_repositories)
]


def get_rate_source_catalog() -> RateSourceCatalog:
    """Register deployable external adapters and the local manual source."""
    registry = ExchangeRateProviderRegistry()
    registry.register(NbuAdapter(NbuClient(dnk_config.CURRENCY.nbu)))
    return RateSourceCatalog(registry)


RateSourceCatalogDep = Annotated[RateSourceCatalog, Depends(get_rate_source_catalog)]

__all__ = [
    "CurrencyRepositories",
    "CurrencyRepositoriesDep",
    "build_repositories",
    "get_rate_source_catalog",
    "RateSourceCatalogDep",
]
