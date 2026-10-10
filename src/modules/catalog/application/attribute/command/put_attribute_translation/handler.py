from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.attribute.command.put_attribute_translation.command import (
    PutAttributeTranslationCommand,
)
from src.modules.catalog.application.attribute.command.put_attribute_translation.dto import (
    PutAttributeTranslationResultDTO,
)


class PutAttributeTranslationHandler:
    """Координирует put_attribute_translation на портах общего tenant UoW."""

    def __init__(
        self,
        repository: AttributeRepositoryProtocol,
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
        self, command: PutAttributeTranslationCommand
    ) -> PutAttributeTranslationResultDTO:
        """Выполняет сценарий; доменные решения и commit остаются у владельцев."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.attribute_id)
        entity.ensure_revision(command.expected_revision)
        locale = LocaleVO(command.locale)
        await self._locales.ensure_active(locale.value)
        entity.put_translation(
            locale, command.label, command.actor_id, self._clock.now()
        )
        await self._repository.save(entity)
        return PutAttributeTranslationResultDTO(entity.id.uuid, entity.revision)
