from src.modules.catalog.application.content_block.command.delete_content_block.command import (
    DeleteContentBlockCommand,
)
from src.modules.catalog.application.content_block.command.delete_content_block.dto import (
    DeleteContentBlockResultDTO,
)
from src.modules.catalog.application.content_block.port.usage_reader import (
    ContentBlockUsageReaderPort,
)
from src.modules.catalog.domain.content_block.error import (
    ContentBlockConflictError,
    ContentBlockNotFoundError,
)
from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)


class DeleteContentBlockHandler:
    def __init__(
        self,
        repository: ContentBlockRepositoryProtocol,
        usage: ContentBlockUsageReaderPort,
    ) -> None:
        self._repository, self._usage = repository, usage

    async def execute(
        self, command: DeleteContentBlockCommand
    ) -> DeleteContentBlockResultDTO:
        block = await self._repository.get_for_update(command.block_id)
        if block is None:
            raise ContentBlockNotFoundError("Content block not found.")
        if block.is_system or await self._usage.is_in_use(command.block_id):
            raise ContentBlockConflictError("Content block is system or in use.")
        await self._repository.delete(block)
        return DeleteContentBlockResultDTO(block.id.uuid)
