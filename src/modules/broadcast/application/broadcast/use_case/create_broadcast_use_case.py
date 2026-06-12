from typing import Protocol

from src.modules.broadcast.application.broadcast.command.create_broadcast import (
    CreateBroadcastCommand,
)
from src.modules.broadcast.application.broadcast.dto.broadcast_dto import BroadcastDTO
from src.modules.broadcast.application.broadcast.repository import (
    BroadcastCommandRepositoryProtocol,
)
from src.modules.broadcast.domain.broadcast.entity import BroadcastEntity
from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.application.uuid import UUIdGeneratorProtocol
from src.modules.shared.domain.time import ClockPort
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


class CreateBroadcastUseCaseProtocol(Protocol):
    """Порт use case создания broadcast."""

    async def __call__(self, command: CreateBroadcastCommand) -> BroadcastDTO:
        """Создает broadcast и возвращает DTO."""
        ...


class CreateBroadcastUseCase:
    """Use case создания draft broadcast definition."""

    def __init__(
        self,
        *,
        command_repository: BroadcastCommandRepositoryProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Инициализирует use case repository, clock и UUID generator портами."""
        self._command_repository = command_repository
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def __call__(self, command: CreateBroadcastCommand) -> BroadcastDTO:
        """Создает draft broadcast и мапит сохраненную entity в DTO."""
        tenant_id = EntityIdVO.from_value(command.tenant_id)
        broadcast_id = BroadcastIdVO.from_value(self._uuid_generator.new())
        broadcast = BroadcastEntity.create(
            _id=broadcast_id,
            title=EntityTitleVO(command.title.strip()),
            description=EntityDescriptionVO.optional(command.description),
            now=self._clock.now(),
        )
        broadcast = await self._command_repository.save(
            tenant_id=tenant_id,
            broadcast=broadcast,
        )
        return self._to_dto(broadcast)

    @staticmethod
    def _to_dto(broadcast: BroadcastEntity) -> BroadcastDTO:
        """Мапит BroadcastEntity в BroadcastDTO."""
        return BroadcastDTO(
            id=broadcast.id.uuid,
            created_at=broadcast.created_at,
            updated_at=broadcast.updated_at,
            title=broadcast.title.value,
            description=(
                None if broadcast.description is None else broadcast.description.value
            ),
            status=broadcast.status.value,
        )
