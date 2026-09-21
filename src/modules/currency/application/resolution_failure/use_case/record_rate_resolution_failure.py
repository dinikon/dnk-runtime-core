from hashlib import sha256
from uuid import uuid4
from src.modules.currency.application.resolution_failure.command.record_failure import (
    RecordRateResolutionFailure,
)
from src.modules.currency.application.resolution_failure.ports import (
    FailureAuditTransactions,
)
from src.modules.currency.domain.resolution_failure.entity import ResolutionFailure
from src.modules.currency.domain.resolution_failure.value_object.id import (
    ResolutionFailureIdVO,
)
from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.shared.domain.time.clock_port import ClockPort


class RecordRateResolutionFailureUseCase:
    """Persist a diagnostic and event independently of a failing caller transaction."""

    def __init__(self, transactions: FailureAuditTransactions, clock: ClockPort):
        self.transactions, self.clock = transactions, clock
        self._recorded: set[str] = set()

    async def __call__(self, command: RecordRateResolutionFailure) -> None:
        key = sha256(
            "|".join(
                str(v)
                for v in (
                    command.tenant_id,
                    command.operation_id,
                    command.source,
                    command.target,
                    command.business_date,
                    command.provider,
                    command.policy_version,
                    command.error_code,
                )
            ).encode()
        ).hexdigest()
        if key in self._recorded:
            return
        failure = ResolutionFailure(
            ResolutionFailureIdVO(uuid4()),
            command.operation_id,
            command.source,
            command.target,
            command.business_date,
            command.provider,
            command.policy_version,
            command.error_code,
            self.clock.now(),
            key,
        )
        async with self.transactions() as tx:
            if await tx.failures.add_once(tenant_id=command.tenant_id, failure=failure):
                await tx.outbox.add(
                    IntegrationEvent(
                        uuid4(),
                        command.tenant_id.uuid,
                        "RateResolutionFailed",
                        1,
                        "currency_resolution_failure",
                        failure.id.uuid,
                        {
                            "operation_id": str(command.operation_id),
                            "source_currency": str(command.source),
                            "target_currency": (
                                str(command.target) if command.target else None
                            ),
                            "business_date": (
                                command.business_date.isoformat()
                                if command.business_date
                                else None
                            ),
                            "provider_code": (
                                str(command.provider) if command.provider else None
                            ),
                            "policy_version": command.policy_version,
                            "error_code": command.error_code,
                        },
                        failure.occurred_at,
                    )
                )
        self._recorded.add(key)


__all__ = ["RecordRateResolutionFailureUseCase"]
