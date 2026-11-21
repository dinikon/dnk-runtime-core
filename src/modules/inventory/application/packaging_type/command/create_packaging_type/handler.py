from src.modules.inventory.application.packaging_type.command.create_packaging_type.command import (
    CreatePackagingTypeCommand,
)
from src.modules.inventory.application.packaging_type.command.create_packaging_type.dto import (
    CreatePackagingTypeResultDTO,
)
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.repository import (
    PackagingTypeRepositoryProtocol,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreatePackagingTypeHandler:
    """Создаёт самостоятельный агрегат через Domain и write-порт внешнего UoW."""

    def __init__(
        self,
        repository: PackagingTypeRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порт записи и общий генератор UUID без доступа к сессии."""
        self._repository = repository
        self._uuid_generator = uuid_generator

    async def execute(
        self, command: CreatePackagingTypeCommand
    ) -> CreatePackagingTypeResultDTO:
        """Вызывает Domain-фабрику и сохраняет новый тип без самостоятельного commit."""
        packaging_type = PackagingType.create(
            identifier=PackagingTypeIdVO.from_value(self._uuid_generator.new()),
            code=PackagingCodeVO(command.code),
            name=PackagingNameVO(command.name),
        )
        await self._repository.add(packaging_type)
        return CreatePackagingTypeResultDTO(
            id=packaging_type.id.uuid,
            code=packaging_type.code.value,
            name=packaging_type.name.value,
            is_active=packaging_type.is_active,
        )
