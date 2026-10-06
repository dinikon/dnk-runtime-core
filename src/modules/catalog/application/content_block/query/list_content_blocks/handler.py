from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ContentBlockListItemDTO,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.query import (
    ListContentBlocksQuery,
)


class ListContentBlocksHandler:
    def __init__(self, repository: ContentBlockQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(
        self, query: ListContentBlocksQuery
    ) -> tuple[ContentBlockListItemDTO, ...]:
        return await self._repository.list()
