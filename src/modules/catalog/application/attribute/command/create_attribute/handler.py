from src.modules.catalog.domain.attribute.aggregate import AttributeDefinition
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.attribute.entity.option import AttributeOption
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.application.attribute.command.create_attribute.command import (
    CreateAttributeCommand,
)
from src.modules.catalog.application.attribute.command.create_attribute.dto import (
    CreateAttributeResultDTO,
)


class CreateAttributeHandler:
    """Координирует create_attribute на портах общего tenant UoW."""

    def __init__(
        self,
        repository: AttributeRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        locales: LocalePort,
    ) -> None:
        """Принимает только необходимые порты текущего сценария."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._uuid = uuid
        self._locales = locales

    async def execute(
        self, command: CreateAttributeCommand
    ) -> CreateAttributeResultDTO:
        """Выполняет сценарий; доменные решения и commit остаются у владельцев."""
        await self._lock.acquire(command.tenant_id)
        locale = LocaleVO(command.locale)
        await self._locales.ensure_active(locale.value)
        if any(option.option_id is not None for option in command.options):
            raise InvalidCatalogValueError("ID новых options создаёт сервер.")
        options = tuple(
            AttributeOption.create(
                AttributeOptionIdVO(self._uuid.new()), o.code, locale, o.label
            )
            for o in command.options
        )
        entity = AttributeDefinition.create(
            AttributeIdVO(self._uuid.new()),
            command.code,
            locale,
            command.label,
            options,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.add(entity)
        return CreateAttributeResultDTO(entity.id.uuid, entity.revision)
