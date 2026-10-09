from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)

from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol

from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.content_block.command.create_content_block.command import (
    CreateContentBlockCommand,
)
from src.modules.catalog.application.content_block.command.create_content_block.dto import (
    CreateContentBlockResultDTO,
)


class CreateContentBlockHandler:
    """Координирует create_content_block; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ContentBlockRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        locales: LocalePort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._uuid = uuid
        self._locales = locales

    async def execute(
        self, command: CreateContentBlockCommand
    ) -> CreateContentBlockResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        await self._locales.ensure_active(LocaleVO(command.locale).value)
        entity = ContentBlockDefinition.create(
            ContentBlockIdVO(self._uuid.new()),
            command.code,
            command.value_type,
            LocaleVO(command.locale),
            command.label,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.add(entity)
        return CreateContentBlockResultDTO(entity.id.uuid, entity.revision)
