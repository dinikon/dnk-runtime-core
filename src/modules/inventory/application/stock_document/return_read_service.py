from dataclasses import replace
from src.modules.inventory.application.stock_document.port.return_query_repository import (
    ReturnDocumentQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_document.query.get_return_document.query import (
    GetReturnDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_return_document.dto import (
    GetReturnDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.query import (
    ListReturnDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.dto import (
    ListReturnDocumentsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class ReturnDocumentReadService:
    """Дополняет собственные проекции публичными именами компаний."""

    def __init__(
        self,
        repository: ReturnDocumentQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты общего UoW."""
        self._repository, self._owners = repository, owners

    async def get(self, query: GetReturnDocumentQuery) -> GetReturnDocumentResultDTO:
        """Читает карточку либо сообщает об отсутствии возврата."""
        result = await self._repository.get(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ возврата не найден.")
        owner = await self._owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner is not None else None)

    async def list(
        self, query: ListReturnDocumentsQuery
    ) -> ListReturnDocumentsResultDTO:
        """Дополняет страницу одним пакетным чтением CRM."""
        page = await self._repository.list(query)
        owners = await self._owners.get_many(
            tuple(dict.fromkeys(item.owner_id for item in page.items))
        )
        return replace(
            page,
            items=tuple(
                replace(
                    item,
                    owner_name=(
                        owner.name
                        if (owner := owners.get(item.owner_id)) is not None
                        else None
                    ),
                )
                for item in page.items
            ),
        )
