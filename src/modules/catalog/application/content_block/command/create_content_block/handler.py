from src.modules.catalog.application.content_block.command.create_content_block.command import (
    CreateContentBlockCommand,
)
from src.modules.catalog.application.content_block.command.create_content_block.dto import (
    CreateContentBlockResultDTO,
)
from src.modules.catalog.application.content_block.port.locale_reader import (
    ContentBlockLocaleReaderPort,
)
from src.modules.catalog.application.content_block.validate_translations import (
    validate_active_translations,
)
from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockCodeVO,
    ContentBlockIdVO,
    ContentBlockTranslationVO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateContentBlockHandler:
    def __init__(
        self,
        repository: ContentBlockRepositoryProtocol,
        locales: ContentBlockLocaleReaderPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository, self._locales, self._uuids = repository, locales, uuids

    async def execute(
        self, command: CreateContentBlockCommand
    ) -> CreateContentBlockResultDTO:
        await validate_active_translations(command.translations, self._locales)
        block = ContentBlockDefinition.create(
            id=ContentBlockIdVO.from_value(self._uuids.new()),
            code=ContentBlockCodeVO(command.code),
            type=command.type,
            translations={
                code: ContentBlockTranslationVO(name)
                for code, name in command.translations.items()
            },
        )
        await self._repository.add(block)
        return CreateContentBlockResultDTO(
            block.id.uuid,
            block.code.value,
            block.type,
            block.is_system,
            {code: item.name for code, item in block.translations.items()},
        )
