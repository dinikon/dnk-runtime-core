from types import SimpleNamespace
from typing import Annotated
from fastapi import Depends

from src.config import dnk_config
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.currency.infrastructure.persistence.repositories import (
    SqlCurrencyDirectory,
    SqlCurrencyPolicyRepository,
    SqlFunctionalCurrencyRepository,
    SqlRateRepository,
)
from src.modules.currency.application.conversion import (
    MoneyConversionService,
    ExchangeRateResolver,
)
from src.modules.currency.application.settings import CurrencySettingsService
from src.modules.currency.application.settings.use_case.get_currency_settings import (
    GetCurrencySettingsUseCase,
)


def build_currency_services(session, clock, naming=None):
    naming = naming or TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    directory = SqlCurrencyDirectory(session)
    policies = SqlCurrencyPolicyRepository(session, naming)
    periods = SqlFunctionalCurrencyRepository(session, naming)
    rates = SqlRateRepository(session, naming)
    resolver = ExchangeRateResolver(rates, policies, directory)
    facade = MoneyConversionService(directory, policies, periods, resolver, clock)
    settings = CurrencySettingsService(
        directory, policies, periods, rates, SqlAlchemyOutboxRepository(session), clock
    )
    return SimpleNamespace(
        directory=directory,
        policies=policies,
        periods=periods,
        rates=rates,
        facade=facade,
        settings=settings,
        get_settings=GetCurrencySettingsUseCase(policies, periods, rates, clock),
        clock=clock,
    )


def get_currency_services(uow: UoWDep, clock: ClockDep):
    return build_currency_services(uow.session, clock)


CurrencyServicesDep = Annotated[SimpleNamespace, Depends(get_currency_services)]
