from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.content_block.command.update_content_block.command import (
    UpdateContentBlockCommand,
)
from src.modules.catalog.application.content_block.command.update_content_block.dto import (
    UpdateContentBlockResultDTO,
)


class UpdateContentBlockHandler:
    """Координирует update_content_block; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ContentBlockRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        locales: LocalePort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._locales = locales

    async def execute(
        self, command: UpdateContentBlockCommand
    ) -> UpdateContentBlockResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.content_block_id)
        entity.ensure_revision(command.expected_revision)
        await self._locales.ensure_active(LocaleVO(command.locale).value)
        entity.update_definition(
            command.value_type,
            LocaleVO(command.locale),
            command.label,
            await self._repository.is_used(entity.id),
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(entity)
        return UpdateContentBlockResultDTO(entity.id.uuid, entity.revision)
