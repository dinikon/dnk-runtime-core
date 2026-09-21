from dataclasses import dataclass
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import Annotated
from uuid import uuid4
from src.config import dnk_config
from src.modules.currency.application.conversion.service import MoneyConversionService
from src.modules.currency.application.conversion.use_case.convert_money import (
    ConvertMoneyUseCase,
)
from src.modules.currency.application.conversion.use_case.convert_money_batch import (
    ConvertMoneyBatchUseCase,
)
from src.modules.currency.application.conversion.use_case.convert_to_functional_currency import (
    ConvertToFunctionalCurrencyUseCase,
)
from src.modules.currency.application.directory.use_case.list_currencies import (
    ListCurrenciesUseCase,
)
from src.modules.currency.application.enabled_currency.use_case.disable_currency import (
    DisableCurrencyUseCase,
)
from src.modules.currency.application.enabled_currency.use_case.enable_currency import (
    EnableCurrencyUseCase,
)
from src.modules.currency.application.enabled_currency.use_case.list_enabled_currencies import (
    ListEnabledCurrenciesUseCase,
)
from src.modules.currency.application.enabled_currency.use_case.set_enabled_currency import (
    SetEnabledCurrencyUseCase,
)
from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.application.exchange_rate.use_case.get_rate_history import (
    GetRateHistoryUseCase,
)
from src.modules.currency.application.exchange_rate.use_case.resolve_exchange_rate import (
    ResolveExchangeRateUseCase,
)
from src.modules.currency.application.facade.currency_facade import CurrencyFacade
from src.modules.currency.application.functional_currency.lifecycle import (
    FunctionalCurrencyLifecycle,
)
from src.modules.currency.application.functional_currency.use_case.activate_functional_currency import (
    ActivateFunctionalCurrencyUseCase,
)
from src.modules.currency.application.functional_currency.use_case.get_functional_currency import (
    GetFunctionalCurrencyUseCase,
)
from src.modules.currency.application.functional_currency.use_case.list_functional_currency_periods import (
    ListFunctionalCurrencyPeriodsUseCase,
)
from src.modules.currency.application.functional_currency.use_case.schedule_functional_currency_change import (
    ScheduleFunctionalCurrencyChangeUseCase,
)
from src.modules.currency.application.manual_rate.use_case.set_manual_rate import (
    SetManualRateUseCase,
)
from src.modules.currency.application.policy.use_case.configure_currency_policy import (
    ConfigureCurrencyPolicyUseCase,
)
from src.modules.currency.application.provider.catalog import RateSourceCatalog
from src.modules.currency.application.provider.use_case.get_provider_status import (
    GetProviderStatusUseCase,
)
from src.modules.currency.application.provider.use_case.list_rate_sources import (
    ListRateSourcesUseCase,
)
from src.modules.currency.application.resolution_failure.use_case.record_rate_resolution_failure import (
    RecordRateResolutionFailureUseCase,
)
from src.modules.currency.application.settings.reader import OperationCurrencySettings
from src.modules.currency.application.settings.use_case.get_currency_settings import (
    GetCurrencySettingsUseCase,
)
from src.modules.currency.application.settings.use_case.initialize_currency import (
    InitializeCurrencyUseCase,
)
from src.modules.currency.domain.exchange_rate.service import ExchangeRateResolver
from src.modules.currency.infrastructure.jobs.activation_scheduler import (
    ScheduledActivationAdapter,
)
from src.modules.currency.infrastructure.persistence.resolution_failure.transactions import (
    SqlFailureAuditTransactions,
)
from src.modules.currency.presentation.depends.infrastructure import (
    RateSourceCatalogDep,
)
from src.modules.currency.presentation.depends.infrastructure import (
    build_repositories,
    get_rate_source_catalog,
    CurrencyRepositories,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.presentation.jobs import build_scheduled_job_repository
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


@dataclass(slots=True)
class CurrencyComponents:
    """Typed transaction components shared by HTTP and consuming contexts."""

    repositories: CurrencyRepositories
    facade: MoneyConversionService
    settings: OperationCurrencySettings
    events: CurrencyEventWriter
    lifecycle: FunctionalCurrencyLifecycle
    sources: RateSourceCatalog
    clock: ClockPort


def build_currency_components(
    session: AsyncSession,
    clock: ClockPort,
    naming: TenantSchemaNaming | None = None,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    operation_id: EntityIdVO | None = None,
) -> CurrencyComponents:
    """Compose build currency components for the current unit of work."""
    naming = naming or TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    repositories = build_repositories(session, naming)
    events = CurrencyEventWriter(SqlAlchemyOutboxRepository(session), clock)
    lifecycle = FunctionalCurrencyLifecycle(
        repositories.periods,
        ScheduledActivationAdapter(build_scheduled_job_repository(session)),
        events,
        clock,
    )
    settings = OperationCurrencySettings(repositories.policies)
    failures = RecordRateResolutionFailureUseCase(
        SqlFailureAuditTransactions(
            session_factory or db_helper.session_factory, naming
        ),
        clock,
    )
    facade = MoneyConversionService(
        repositories.directory,
        repositories.policies,
        repositories.periods,
        ExchangeRateResolver(
            repositories.rates,
            repositories.policies,
            repositories.directory,
            repositories.enabled,
        ),
        clock,
        settings,
        failures,
        operation_id or EntityIdVO(uuid4()),
        repositories.enabled,
    )
    return CurrencyComponents(
        repositories,
        facade,
        settings,
        events,
        lifecycle,
        get_rate_source_catalog(),
        clock,
    )


def get_currency_components(
    uow: UoWDep, clock: ClockDep, request: Request
) -> CurrencyComponents:
    """Compose currency components for the current unit of work."""
    return build_currency_components(
        uow.session,
        clock,
        session_factory=getattr(request.app.state, "db", db_helper.session_factory),
    )


CurrencyComponentsDep = Annotated[CurrencyComponents, Depends(get_currency_components)]


def get_initialize_currency_use_case(
    c: CurrencyComponentsDep,
) -> InitializeCurrencyUseCase:
    """Compose the initialize currency application scenario."""
    r = c.repositories
    return InitializeCurrencyUseCase(
        r.directory,
        r.policies,
        r.enabled,
        r.periods,
        c.events,
        c.clock,
        c.sources,
        c.lifecycle,
    )


InitializeCurrencyUseCaseDep = Annotated[
    InitializeCurrencyUseCase, Depends(get_initialize_currency_use_case)
]


def get_configure_currency_policy_use_case(
    c: CurrencyComponentsDep,
) -> ConfigureCurrencyPolicyUseCase:
    """Compose the configure currency policy application scenario."""
    r = c.repositories
    return ConfigureCurrencyPolicyUseCase(
        r.directory,
        r.policies,
        r.enabled,
        r.periods,
        c.events,
        c.clock,
        c.sources,
        c.lifecycle,
    )


ConfigureCurrencyPolicyUseCaseDep = Annotated[
    ConfigureCurrencyPolicyUseCase, Depends(get_configure_currency_policy_use_case)
]


def get_set_enabled_currency_use_case(
    c: CurrencyComponentsDep,
) -> SetEnabledCurrencyUseCase:
    """Compose the set enabled currency application scenario."""
    r = c.repositories
    return SetEnabledCurrencyUseCase(
        r.directory, r.policies, r.enabled, r.periods, c.events, c.clock
    )


SetEnabledCurrencyUseCaseDep = Annotated[
    SetEnabledCurrencyUseCase, Depends(get_set_enabled_currency_use_case)
]


def get_schedule_functional_currency_change_use_case(
    c: CurrencyComponentsDep,
) -> ScheduleFunctionalCurrencyChangeUseCase:
    """Compose the schedule functional currency change application scenario."""
    r = c.repositories
    return ScheduleFunctionalCurrencyChangeUseCase(
        r.directory, r.policies, r.enabled, r.periods, c.events, c.clock, c.lifecycle
    )


ScheduleFunctionalCurrencyChangeUseCaseDep = Annotated[
    ScheduleFunctionalCurrencyChangeUseCase,
    Depends(get_schedule_functional_currency_change_use_case),
]


def get_set_manual_rate_use_case(c: CurrencyComponentsDep) -> SetManualRateUseCase:
    """Compose the set manual rate application scenario."""
    r = c.repositories
    return SetManualRateUseCase(
        r.directory, r.policies, r.enabled, r.manual, c.events, c.clock
    )


SetManualRateUseCaseDep = Annotated[
    SetManualRateUseCase, Depends(get_set_manual_rate_use_case)
]


def get_get_currency_settings_use_case(
    c: CurrencyComponentsDep,
) -> GetCurrencySettingsUseCase:
    """Compose get currency settings."""
    return GetCurrencySettingsUseCase(
        c.repositories.policies,
        c.repositories.periods,
        c.repositories.provider,
        c.clock,
        c.repositories.enabled,
    )


GetCurrencySettingsUseCaseDep = Annotated[
    GetCurrencySettingsUseCase, Depends(get_get_currency_settings_use_case)
]


def get_list_currencies_use_case(c: CurrencyComponentsDep) -> ListCurrenciesUseCase:
    """Compose list currencies."""
    return ListCurrenciesUseCase(c.repositories.directory)


ListCurrenciesUseCaseDep = Annotated[
    ListCurrenciesUseCase, Depends(get_list_currencies_use_case)
]


def get_list_enabled_currencies_use_case(
    c: CurrencyComponentsDep,
) -> ListEnabledCurrenciesUseCase:
    """Compose list enabled currencies."""
    return ListEnabledCurrenciesUseCase(c.repositories.enabled)


ListEnabledCurrenciesUseCaseDep = Annotated[
    ListEnabledCurrenciesUseCase, Depends(get_list_enabled_currencies_use_case)
]


def get_list_functional_currency_periods_use_case(
    c: CurrencyComponentsDep,
) -> ListFunctionalCurrencyPeriodsUseCase:
    """Compose list functional currency periods."""
    return ListFunctionalCurrencyPeriodsUseCase(c.repositories.periods)


ListFunctionalCurrencyPeriodsUseCaseDep = Annotated[
    ListFunctionalCurrencyPeriodsUseCase,
    Depends(get_list_functional_currency_periods_use_case),
]


def get_get_functional_currency_use_case(
    c: CurrencyComponentsDep,
) -> GetFunctionalCurrencyUseCase:
    """Compose get functional currency."""
    return GetFunctionalCurrencyUseCase(c.facade)


GetFunctionalCurrencyUseCaseDep = Annotated[
    GetFunctionalCurrencyUseCase, Depends(get_get_functional_currency_use_case)
]


def get_get_rate_history_use_case(c: CurrencyComponentsDep) -> GetRateHistoryUseCase:
    """Compose get rate history."""
    return GetRateHistoryUseCase(c.repositories.rates)


GetRateHistoryUseCaseDep = Annotated[
    GetRateHistoryUseCase, Depends(get_get_rate_history_use_case)
]


def get_resolve_exchange_rate_use_case(
    c: CurrencyComponentsDep,
) -> ResolveExchangeRateUseCase:
    """Compose resolve exchange rate."""
    return ResolveExchangeRateUseCase(c.facade)


ResolveExchangeRateUseCaseDep = Annotated[
    ResolveExchangeRateUseCase, Depends(get_resolve_exchange_rate_use_case)
]


def get_get_provider_status_use_case(
    c: CurrencyComponentsDep,
) -> GetProviderStatusUseCase:
    """Compose get provider status."""
    return GetProviderStatusUseCase(c.repositories.provider)


GetProviderStatusUseCaseDep = Annotated[
    GetProviderStatusUseCase, Depends(get_get_provider_status_use_case)
]


def get_activate_functional_currency_use_case(
    c: CurrencyComponentsDep,
) -> ActivateFunctionalCurrencyUseCase:
    """Compose activate functional currency."""
    return ActivateFunctionalCurrencyUseCase(
        c.repositories.policies, c.repositories.periods, c.lifecycle
    )


ActivateFunctionalCurrencyUseCaseDep = Annotated[
    ActivateFunctionalCurrencyUseCase,
    Depends(get_activate_functional_currency_use_case),
]


def get_currency_facade(c: CurrencyComponentsDep) -> MoneyConversionService:
    """Compose currency facade for the current unit of work."""
    return c.facade


CurrencyFacadeDep = Annotated[CurrencyFacade, Depends(get_currency_facade)]


def get_list_rate_sources_use_case(
    catalog: RateSourceCatalogDep,
) -> ListRateSourcesUseCase:
    """Compose list rate sources use case for the current unit of work."""
    return ListRateSourcesUseCase(catalog)


ListRateSourcesUseCaseDep = Annotated[
    ListRateSourcesUseCase, Depends(get_list_rate_sources_use_case)
]


def get_enable_currency_use_case(
    change: SetEnabledCurrencyUseCaseDep,
) -> EnableCurrencyUseCase:
    """Compose enable currency use case for the current unit of work."""
    return EnableCurrencyUseCase(change)


EnableCurrencyUseCaseDep = Annotated[
    EnableCurrencyUseCase, Depends(get_enable_currency_use_case)
]


def get_disable_currency_use_case(
    change: SetEnabledCurrencyUseCaseDep,
) -> DisableCurrencyUseCase:
    """Compose disable currency use case for the current unit of work."""
    return DisableCurrencyUseCase(change)


DisableCurrencyUseCaseDep = Annotated[
    DisableCurrencyUseCase, Depends(get_disable_currency_use_case)
]


def get_convert_money_use_case(facade: CurrencyFacadeDep) -> ConvertMoneyUseCase:
    """Compose convert money use case for the current unit of work."""
    return ConvertMoneyUseCase(facade)


ConvertMoneyUseCaseDep = Annotated[
    ConvertMoneyUseCase, Depends(get_convert_money_use_case)
]


def get_convert_to_functional_currency_use_case(
    facade: CurrencyFacadeDep,
) -> ConvertToFunctionalCurrencyUseCase:
    """Compose convert to functional currency use case for the current unit of work."""
    return ConvertToFunctionalCurrencyUseCase(facade)


ConvertToFunctionalCurrencyUseCaseDep = Annotated[
    ConvertToFunctionalCurrencyUseCase,
    Depends(get_convert_to_functional_currency_use_case),
]


def get_convert_money_batch_use_case(
    facade: CurrencyFacadeDep,
) -> ConvertMoneyBatchUseCase:
    """Compose convert money batch use case for the current unit of work."""
    return ConvertMoneyBatchUseCase(facade)


ConvertMoneyBatchUseCaseDep = Annotated[
    ConvertMoneyBatchUseCase, Depends(get_convert_money_batch_use_case)
]


__all__ = [
    "CurrencyComponents",
    "build_currency_components",
    "get_currency_components",
    "get_initialize_currency_use_case",
    "get_configure_currency_policy_use_case",
    "get_set_enabled_currency_use_case",
    "get_schedule_functional_currency_change_use_case",
    "get_set_manual_rate_use_case",
    "get_get_currency_settings_use_case",
    "get_list_currencies_use_case",
    "get_list_enabled_currencies_use_case",
    "get_list_functional_currency_periods_use_case",
    "get_get_functional_currency_use_case",
    "get_get_rate_history_use_case",
    "get_resolve_exchange_rate_use_case",
    "get_get_provider_status_use_case",
    "get_activate_functional_currency_use_case",
    "get_currency_facade",
    "get_list_rate_sources_use_case",
    "get_enable_currency_use_case",
    "get_disable_currency_use_case",
    "get_convert_money_use_case",
    "get_convert_to_functional_currency_use_case",
    "get_convert_money_batch_use_case",
]
