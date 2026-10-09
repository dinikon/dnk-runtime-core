from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product_type.command.put_product_type_translation.command import (
    PutProductTypeTranslationCommand,
)
from src.modules.catalog.application.product_type.command.put_product_type_translation.dto import (
    PutProductTypeTranslationResultDTO,
)


class PutProductTypeTranslationHandler:
    """Координирует put_product_type_translation; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductTypeRepositoryProtocol,
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
        self, command: PutProductTypeTranslationCommand
    ) -> PutProductTypeTranslationResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.product_type_id)
        entity.ensure_revision(command.expected_revision)
        await self._locales.ensure_active(LocaleVO(command.locale).value)
        entity.put_translation(
            LocaleVO(command.locale), command.label, command.actor_id, self._clock.now()
        )
        await self._repository.save(entity)
        return PutProductTypeTranslationResultDTO(entity.id.uuid, entity.revision)
