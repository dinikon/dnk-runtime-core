from src.modules.catalog.application.attribute.port.query_repository import (
    AttributeQueryRepositoryProtocol,
)
from src.modules.catalog.application.attribute.query.get_attribute.dto import (
    GetAttributeResultDTO,
)
from src.modules.catalog.application.attribute.query.get_attribute.query import (
    GetAttributeQuery,
)
from src.modules.catalog.domain.attribute.error import AttributeNotFoundError


class GetAttributeHandler:
    def __init__(self, repository: AttributeQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: GetAttributeQuery) -> GetAttributeResultDTO:
        result = await self._repository.get_details(query.attribute_id, query.locale)
        if result is None:
            raise AttributeNotFoundError("Attribute not found.")
        return result
