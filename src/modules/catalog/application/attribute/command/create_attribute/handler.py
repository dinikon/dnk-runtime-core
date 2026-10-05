from src.modules.catalog.application.attribute.command.create_attribute.command import (
    CreateAttributeCommand,
    CreateAttributeContent,
)
from src.modules.catalog.application.attribute.command.create_attribute.dto import (
    CreatedAttributeOptionDTO,
    CreateAttributeResultDTO,
)
from src.modules.catalog.application.attribute.port.locale_reader import (
    AttributeLocaleReaderPort,
)
from src.modules.catalog.domain.attribute.aggregate import (
    Attribute,
    AttributeContent,
    AttributeOption,
)
from src.modules.catalog.domain.attribute.error import AttributeLocaleUnavailableError
from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def _content(items: tuple[CreateAttributeContent, ...]) -> tuple[AttributeContent, ...]:
    return tuple(
        AttributeContent(AttributeLocaleVO(item.locale), item.name) for item in items
    )


class CreateAttributeHandler:
    def __init__(
        self,
        repository: AttributeRepositoryProtocol,
        locales: AttributeLocaleReaderPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository = repository
        self._locales = locales
        self._clock = clock
        self._uuids = uuids

    async def execute(
        self, command: CreateAttributeCommand
    ) -> CreateAttributeResultDTO:
        contents = _content(command.contents)
        options = tuple(
            AttributeOption(
                id=EntityIdVO.from_value(self._uuids.new()),
                code=item.code,
                contents=_content(item.contents),
            )
            for item in command.options
        )
        for code in {
            item.locale.value
            for item in contents
            + tuple(c for option in options for c in option.contents)
        }:
            if not await self._locales.is_active(code):
                raise AttributeLocaleUnavailableError("Attribute locale is not active.")
        attribute = Attribute.create(
            attribute_id=EntityIdVO.from_value(self._uuids.new()),
            code=command.code,
            options=options,
            contents=contents,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(attribute)
        return CreateAttributeResultDTO(
            id=attribute.id.uuid,
            code=attribute.code,
            options=tuple(
                CreatedAttributeOptionDTO(option.id.uuid, option.code)
                for option in attribute.options
            ),
            created_at=attribute.created_at,
            updated_at=attribute.updated_at,
            created_by=attribute.created_by.uuid,
            updated_by=attribute.updated_by.uuid,
        )
