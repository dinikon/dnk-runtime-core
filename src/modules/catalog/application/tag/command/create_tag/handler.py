from src.modules.catalog.domain.tag.aggregate import Tag
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.domain.tag.repository import TagRepositoryProtocol
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.application.tag.command.create_tag.command import (
    CreateTagCommand,
)
from src.modules.catalog.application.tag.command.create_tag.dto import (
    CreateTagResultDTO,
)


class CreateTagHandler:
    """Координирует создание tag на портах общего tenant UoW."""

    def __init__(
        self,
        repository: TagRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        locales: LocalePort,
    ) -> None:
        """Принимает необходимые порты без привязки к SQL."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._uuid = uuid
        self._locales = locales

    async def execute(self, command: CreateTagCommand) -> CreateTagResultDTO:
        """Проверяет locale и создаёт агрегат; commit выполняет внешняя сборка."""
        await self._lock.acquire(command.tenant_id)
        locale = LocaleVO(command.locale)
        await self._locales.ensure_active(locale.value)
        entity = Tag.create(
            TagIdVO(self._uuid.new()),
            locale,
            command.label,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.add(entity)
        return CreateTagResultDTO(entity.id.uuid, entity.revision)
