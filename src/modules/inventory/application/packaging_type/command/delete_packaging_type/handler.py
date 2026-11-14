from src.modules.inventory.application.packaging_type.command.delete_packaging_type.command import (
    DeletePackagingTypeCommand,
)
from src.modules.inventory.application.packaging_type.port.usage import (
    PackagingTypeUsagePort,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.packaging_type.repository import (
    PackagingTypeRepositoryProtocol,
)


class DeletePackagingTypeHandler:
    """Координирует удаление после доменной проверки в транзакции внешнего UoW."""

    def __init__(
        self, repository: PackagingTypeRepositoryProtocol, usage: PackagingTypeUsagePort
    ) -> None:
        """Принимает порты корня и использования на одной сессии внешнего tenant-UoW."""
        self._repository = repository
        self._usage = usage

    async def execute(self, command: DeletePackagingTypeCommand) -> None:
        """Блокирует тип, получает снимок использования и делегирует запрет Domain."""
        packaging_type = await self._repository.get_for_update(
            command.packaging_type_id
        )
        if packaging_type is None:
            raise PackagingTypeNotFoundError("Тип тары не найден.")
        packaging_type.ensure_can_delete(await self._usage.get(packaging_type.id))
        await self._repository.delete(packaging_type)
