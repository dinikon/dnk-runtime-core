from uuid import uuid4
from src.modules.identity.application.user.command.set_display_currency_command import (
    SetDisplayCurrencyCommand,
)
from src.modules.identity.application.user.dto.display_currency_dto import (
    DisplayCurrencyDTO,
)
from src.modules.identity.application.user.ports.display_currency import (
    DisplayCurrencyValidator,
    DisplayCurrencyPreferenceRepository,
)
from src.modules.identity.domain.auth import InvalidSessionError
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)


class SetDisplayCurrencyUseCase:
    """Update the authenticated user's interface currency in the shared UoW."""

    def __init__(
        self,
        users: DisplayCurrencyPreferenceRepository,
        validator: DisplayCurrencyValidator,
        outbox: OutboxRepositoryProtocol,
        clock: ClockPort,
    ):
        self.users, self.validator, self.outbox, self.clock = (
            users,
            validator,
            outbox,
            clock,
        )

    async def __call__(self, command: SetDisplayCurrencyCommand) -> DisplayCurrencyDTO:
        if command.currency is not None:
            await self.validator.validate(
                tenant_id=command.tenant_id, currency=command.currency
            )
        user = await self.users.get_by_id(command.user_id, tenant_id=command.tenant_id)
        if user is None or user.tenant_id != command.tenant_id or not user.can_login():
            raise InvalidSessionError()
        if user.update_display_currency(command.currency, self.clock.now()):
            await self.users.save_display_currency(user, tenant_id=command.tenant_id)
            await self.outbox.add(
                IntegrationEvent(
                    uuid4(),
                    command.tenant_id.uuid,
                    "UserDisplayCurrencyChanged",
                    1,
                    "user",
                    command.user_id.uuid,
                    {
                        "actor_id": str(command.user_id),
                        "display_currency": (
                            str(command.currency) if command.currency else None
                        ),
                    },
                    self.clock.now(),
                )
            )
        return DisplayCurrencyDTO(user.display_currency)


__all__ = ["SetDisplayCurrencyUseCase"]
