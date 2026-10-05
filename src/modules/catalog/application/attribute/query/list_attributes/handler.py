from src.modules.catalog.application.attribute.port.query_repository import (
    AttributeQueryRepositoryProtocol,
)
from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    AttributeDetailsDTO,
)
from src.modules.catalog.application.attribute.query.list_attributes.query import (
    ListAttributesQuery,
)


class ListAttributesHandler:
    def __init__(self, repository: AttributeQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(
        self, query: ListAttributesQuery
    ) -> tuple[AttributeDetailsDTO, ...]:
        return await self._repository.list_details(query.locale)
