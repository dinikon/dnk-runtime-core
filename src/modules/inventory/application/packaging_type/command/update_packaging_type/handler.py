from src.modules.inventory.application.packaging_type.command.update_packaging_type.command import (
    UpdatePackagingTypeCommand,
)
from src.modules.inventory.application.packaging_type.command.update_packaging_type.dto import (
    UpdatePackagingTypeResultDTO,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.packaging_type.repository import (
    PackagingTypeRepositoryProtocol,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO


class UpdatePackagingTypeHandler:
    """Координирует изменение типа тары через Domain в общем внешнем UoW."""

    def __init__(self, repository: PackagingTypeRepositoryProtocol) -> None:
        """Принимает write-порт без доступа к сессии и управлению транзакцией."""
        self._repository = repository

    async def execute(
        self, command: UpdatePackagingTypeCommand
    ) -> UpdatePackagingTypeResultDTO:
        """Блокирует актуальный корень, применяет Domain-методы и пропускает no-op."""
        packaging_type = await self._repository.get_for_update(
            command.packaging_type_id
        )
        if packaging_type is None:
            raise PackagingTypeNotFoundError("Тип тары не найден.")
        updated = packaging_type
        if "code" in command.fields and command.code is not None:
            updated = updated.change_code(PackagingCodeVO(command.code))
        if "name" in command.fields and command.name is not None:
            updated = updated.rename(PackagingNameVO(command.name))
        if "is_active" in command.fields:
            updated = updated.activate() if command.is_active else updated.deactivate()
        if updated != packaging_type:
            await self._repository.save(updated)
        return UpdatePackagingTypeResultDTO(
            id=updated.id.uuid,
            code=updated.code.value,
            name=updated.name.value,
            is_active=updated.is_active,
        )
