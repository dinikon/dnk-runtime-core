from src.modules.currency.application.functional_currency.command.activate_functional_currency_command import (
    ActivateFunctionalCurrencyCommand,
)
from src.modules.currency.application.functional_currency.use_case.activate_functional_currency import (
    ActivateFunctionalCurrencyUseCase,
)
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.currency.presentation.depends.application import (
    build_currency_components,
)
from src.modules.shared.domain.jobs import ScheduledJob
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork
from src.modules.shared.infrastructure.time.utc_clock import UtcClock


class FunctionalCurrencyActivationHandler:
    """Adapt a tenant job to the idempotent activation application scenario."""

    def __init__(self, session_factory, clock=None):
        self.session_factory, self.clock = session_factory, clock or UtcClock()

    async def handle(self, job: ScheduledJob) -> None:
        period_id = FunctionalCurrencyPeriodIdVO.from_value(job.payload["period_id"])
        async with UnitOfWork(self.session_factory) as uow:
            components = build_currency_components(
                uow.session, self.clock, session_factory=self.session_factory
            )
            await ActivateFunctionalCurrencyUseCase(
                components.repositories.policies,
                components.repositories.periods,
                components.lifecycle,
            )(
                ActivateFunctionalCurrencyCommand(
                    EntityIdVO.from_value(job.tenant_id), period_id
                )
            )


__all__ = ["FunctionalCurrencyActivationHandler"]
