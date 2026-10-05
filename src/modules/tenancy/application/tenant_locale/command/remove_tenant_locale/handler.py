from src.modules.tenancy.application.tenant_locale.command.remove_tenant_locale.command import (
    RemoveTenantLocaleCommand,
)
from src.modules.tenancy.domain.tenant_locale.error import (
    TenantLocaleNotSelectedError,
)
from src.modules.tenancy.domain.tenant_locale.repository import (
    TenantLocaleRepositoryProtocol,
)
from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)


class RemoveTenantLocaleHandler:
    """Удаляет только выбор локали; переводы не затрагивает."""

    def __init__(self, repository: TenantLocaleRepositoryProtocol):
        self._repository = repository

    async def execute(self, command: RemoveTenantLocaleCommand) -> None:
        removed = await self._repository.remove(TenantLocaleCodeVO(command.code))
        if not removed:
            raise TenantLocaleNotSelectedError("Locale is not selected.")
