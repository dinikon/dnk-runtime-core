from src.modules.catalog.application.content_block.command.put_content_block.command import (
    PutContentBlockCommand,
)
from src.modules.catalog.application.content_block.command.put_content_block.dto import (
    PutContentBlockResultDTO,
)
from src.modules.catalog.application.content_block.port.locale_reader import (
    ContentBlockLocaleReaderPort,
)
from src.modules.catalog.application.content_block.port.usage_reader import (
    ContentBlockUsageReaderPort,
)
from src.modules.catalog.application.content_block.validate_translations import (
    validate_active_translations,
)
from src.modules.catalog.domain.content_block.error import (
    ContentBlockConflictError,
    ContentBlockNotFoundError,
)
from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockTranslationVO,
)


class PutContentBlockHandler:
    def __init__(
        self,
        repository: ContentBlockRepositoryProtocol,
        usage: ContentBlockUsageReaderPort,
        locales: ContentBlockLocaleReaderPort,
    ) -> None:
        self._repository, self._usage, self._locales = repository, usage, locales

    async def execute(
        self, command: PutContentBlockCommand
    ) -> PutContentBlockResultDTO:
        await validate_active_translations(command.translations, self._locales)
        block = await self._repository.get_for_update(command.block_id)
        if block is None:
            raise ContentBlockNotFoundError("Content block not found.")
        if command.type != block.type:
            if block.is_system:
                raise ContentBlockConflictError(
                    "System content block type cannot be changed."
                )
            if await self._usage.is_in_use(command.block_id):
                raise ContentBlockConflictError(
                    "Used content block type cannot be changed."
                )
            block.change_type(command.type)
        block.replace_translations(
            {
                code: ContentBlockTranslationVO(name)
                for code, name in command.translations.items()
            }
        )
        await self._repository.save(block)
        return PutContentBlockResultDTO(
            block.id.uuid,
            block.code.value,
            block.type,
            block.is_system,
            {code: item.name for code, item in block.translations.items()},
        )
