from dataclasses import replace
from src.modules.inventory.application.stock_document.port.internal_move_query_repository import (
    InternalMoveDocumentQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.query import (
    GetInternalMoveDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.dto import (
    GetInternalMoveDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.query import (
    ListInternalMoveDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.dto import (
    ListInternalMoveDocumentsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class InternalMoveDocumentReadService:
    """Дополняет собственные проекции публичными именами компаний."""

    def __init__(
        self,
        repository: InternalMoveDocumentQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты общего UoW."""
        self._repository, self._owners = repository, owners

    async def get(
        self, query: GetInternalMoveDocumentQuery
    ) -> GetInternalMoveDocumentResultDTO:
        """Читает карточку либо сообщает об отсутствии перемещения."""
        result = await self._repository.get(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ перемещения не найден.")
        owner = await self._owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner is not None else None)

    async def list(
        self, query: ListInternalMoveDocumentsQuery
    ) -> ListInternalMoveDocumentsResultDTO:
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
