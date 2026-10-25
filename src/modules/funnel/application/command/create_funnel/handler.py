from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.funnel.application.command.create_funnel.command import (
    CreateFunnelCommand,
)
from src.modules.funnel.application.command.create_funnel.dto import (
    CreateFunnelResultDTO,
)
from src.modules.funnel.domain.aggregate import Funnel
from src.modules.funnel.domain.stage import Stage
from src.modules.funnel.domain.repository import FunnelRepositoryProtocol
from src.modules.funnel.domain.error import FunnelError, FunnelNotFoundError
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class CreateFunnelHandler:
    """Координирует create процесса в текущем UoW."""

    def __init__(
        self,
        repository: FunnelRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает только порты хранения, ID и времени."""
        self._repository = repository
        self._uuid = uuid
        self._clock = clock

    async def execute(self, command: CreateFunnelCommand) -> CreateFunnelResultDTO:
        """Вызывает доменные правила и сохраняет результат без commit."""
        existing = set()
        stages = []
        mapping = {}
        keys = set()
        for value in command.stages:
            if value.id is not None and value.id not in existing:
                raise FunnelError("Чужой или неизвестный ID стадии.")
            if value.id is None and (not value.client_key or value.client_key in keys):
                raise FunnelError("Нужен уникальный client_key новой стадии.")
            stage_id = value.id or self._uuid.new()
            if value.client_key:
                keys.add(value.client_key)
                mapping[value.client_key] = stage_id
            stages.append(
                Stage.create(
                    stage_id=EntityIdVO(stage_id), name=value.name, color=value.color
                )
            )
        entity = Funnel.create(
            funnel_id=EntityIdVO(self._uuid.new()),
            model_key=command.model_key,
            name=command.name,
            stages=tuple(stages),
            actor_id=EntityIdVO(command.actor_id),
            now=self._clock.now(),
        )
        await self._repository.add(entity)
        return CreateFunnelResultDTO(entity.id.uuid, entity.revision, mapping)
