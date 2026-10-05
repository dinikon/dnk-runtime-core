from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.tenancy.application.tenant_locale.command.add_tenant_locale.command import (
    AddTenantLocaleCommand,
)
from src.modules.tenancy.application.tenant_locale.command.add_tenant_locale.dto import (
    AddTenantLocaleResultDTO,
)
from src.modules.tenancy.domain.tenant_locale.aggregate import TenantLocale
from src.modules.tenancy.domain.tenant_locale.repository import (
    TenantLocaleRepositoryProtocol,
)


class AddTenantLocaleHandler:
    """Добавляет выбранную локаль без управления транзакцией."""

    def __init__(self, repository: TenantLocaleRepositoryProtocol, clock: ClockPort):
        self._repository = repository
        self._clock = clock

    async def execute(
        self, command: AddTenantLocaleCommand
    ) -> AddTenantLocaleResultDTO:
        locale = TenantLocale.create(
            code=command.code,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(locale)
        return AddTenantLocaleResultDTO(
            code=locale.code.value,
            created_at=locale.created_at,
            created_by=locale.created_by.uuid,
        )
