from src.modules.catalog.domain.tag.repository import TagRepositoryProtocol
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.tag.command.put_tag_translation.command import (
    PutTagTranslationCommand,
)
from src.modules.catalog.application.tag.command.put_tag_translation.dto import (
    PutTagTranslationResultDTO,
)


class PutTagTranslationHandler:
    """Координирует put_tag_translation на портах общего tenant UoW."""

    def __init__(
        self,
        repository: TagRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        locales: LocalePort,
    ) -> None:
        """Принимает только необходимые порты текущего сценария."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._locales = locales

    async def execute(
        self, command: PutTagTranslationCommand
    ) -> PutTagTranslationResultDTO:
        """Выполняет сценарий; доменные решения и commit остаются у владельцев."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.tag_id)
        entity.ensure_revision(command.expected_revision)
        locale = LocaleVO(command.locale)
        await self._locales.ensure_active(locale.value)
        entity.put_translation(
            locale, command.label, command.actor_id, self._clock.now()
        )
        await self._repository.save(entity)
        return PutTagTranslationResultDTO(entity.id.uuid, entity.revision)
