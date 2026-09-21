"""Test fixtures for independent Currency application scenarios."""

from types import SimpleNamespace
from src.modules.currency.presentation.depends.application import (
    build_currency_components,
    get_initialize_currency_use_case,
    get_configure_currency_policy_use_case,
    get_set_enabled_currency_use_case,
    get_schedule_functional_currency_change_use_case,
    get_set_manual_rate_use_case,
)
from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.application.settings.use_case.initialize_currency import (
    InitializeCurrencyUseCase,
)
from src.modules.currency.application.policy.use_case.configure_currency_policy import (
    ConfigureCurrencyPolicyUseCase,
)
from src.modules.currency.application.enabled_currency.use_case.set_enabled_currency import (
    SetEnabledCurrencyUseCase,
)
from src.modules.currency.application.functional_currency.use_case.schedule_functional_currency_change import (
    ScheduleFunctionalCurrencyChangeUseCase,
)
from src.modules.currency.application.manual_rate.use_case.set_manual_rate import (
    SetManualRateUseCase,
)
from src.modules.currency.presentation.depends.infrastructure import (
    get_rate_source_catalog,
)
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import async_sessionmaker


def configuration_cases(directory, policies, periods, rates, outbox, clock):
    events = CurrencyEventWriter(outbox, clock)
    sources = get_rate_source_catalog()
    lifecycle = SimpleNamespace(ensure=AsyncMock())
    common = (directory, policies, policies, periods, events, clock)
    return SimpleNamespace(
        initialize=InitializeCurrencyUseCase(*common, sources, lifecycle),
        configure=ConfigureCurrencyPolicyUseCase(*common, sources, lifecycle),
        set_enabled=SetEnabledCurrencyUseCase(*common),
        schedule=ScheduleFunctionalCurrencyChangeUseCase(*common, lifecycle),
        set_manual_rate=SetManualRateUseCase(
            directory, policies, policies, rates, events, clock
        ),
    )


def fixture_components(session, clock, naming):
    c = build_currency_components(
        session,
        clock,
        naming,
        session_factory=async_sessionmaker(session.bind, expire_on_commit=False),
    )
    return SimpleNamespace(
        components=c,
        facade=c.facade,
        reader=c.settings,
        clock=c.clock,
        rates=c.repositories.rates,
        policies=c.repositories.policies,
        periods=c.repositories.periods,
        settings=SimpleNamespace(
            initialize=get_initialize_currency_use_case(c),
            configure=get_configure_currency_policy_use_case(c),
            set_enabled=get_set_enabled_currency_use_case(c),
            schedule=get_schedule_functional_currency_change_use_case(c),
            set_manual_rate=get_set_manual_rate_use_case(c),
        ),
    )
