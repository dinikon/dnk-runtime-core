from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    ContentBlockDetailsDTO,
)
from src.modules.catalog.application.content_block.query.get_content_block.query import (
    GetContentBlockQuery,
)
from src.modules.catalog.domain.content_block.error import ContentBlockNotFoundError


class GetContentBlockHandler:
    def __init__(self, repository: ContentBlockQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: GetContentBlockQuery) -> ContentBlockDetailsDTO:
        result = await self._repository.get(query.block_id)
        if result is None:
            raise ContentBlockNotFoundError("Content block not found.")
        return result
