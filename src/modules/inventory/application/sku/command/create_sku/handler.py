from src.modules.inventory.application.sku.command.create_sku.command import (
    CreateSkuCommand,
)
from src.modules.inventory.application.sku.command.create_sku.dto import (
    CreateSkuResultDTO,
)
from src.modules.inventory.domain.sku.aggregate import Sku
from src.modules.inventory.domain.sku.repository import SkuRepositoryProtocol
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class CreateSkuHandler:
    """Создаёт агрегат и сохраняет его в уже открытом внешнем UoW."""

    def __init__(
        self,
        repository: SkuRepositoryProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def execute(self, command: CreateSkuCommand) -> CreateSkuResultDTO:
        """Возвращает нормализованную учётную позицию после записи."""
        sku = Sku.create(
            sku_id=SkuIdVO.from_value(self._uuid_generator.new()),
            code=command.code,
            title=command.title,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(sku)
        return CreateSkuResultDTO(
            id=sku.id.uuid,
            code=sku.code.value,
            title=sku.title.value,
            created_at=sku.created_at,
            updated_at=sku.updated_at,
            created_by=sku.created_by.uuid,
            updated_by=sku.updated_by.uuid,
        )
