from src.modules.catalog.domain.attribute.entity.option import AttributeOption
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.application.attribute.command.replace_attribute_options.command import (
    ReplaceAttributeOptionsCommand,
)
from src.modules.catalog.application.attribute.command.replace_attribute_options.dto import (
    ReplaceAttributeOptionsResultDTO,
)


class ReplaceAttributeOptionsHandler:
    """Координирует replace_attribute_options на портах общего tenant UoW."""

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
        self, command: ReplaceAttributeOptionsCommand
    ) -> ReplaceAttributeOptionsResultDTO:
        """Выполняет сценарий; доменные решения и commit остаются у владельцев."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.attribute_id)
        entity.ensure_revision(command.expected_revision)
        locale = LocaleVO(command.locale)
        await self._locales.ensure_active(locale.value)
        options = []
        for value in command.options:
            if value.option_id is None:
                option = AttributeOption.create(
                    AttributeOptionIdVO(self._uuid.new()),
                    value.code,
                    locale,
                    value.label,
                )
            else:
                original = entity.get_option(value.option_id)
                option = AttributeOption.restore(
                    original.id,
                    value.code,
                    {**original.translations, locale.value: value.label},
                )
            options.append(option)
        used = await self._repository.used_options(entity.id)
        entity.replace_options(
            tuple(options), used, command.actor_id, self._clock.now()
        )
        await self._repository.save(entity)
        return ReplaceAttributeOptionsResultDTO(entity.id.uuid, entity.revision)
