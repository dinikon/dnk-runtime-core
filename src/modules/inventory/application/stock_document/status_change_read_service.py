from dataclasses import replace
from src.modules.inventory.application.stock_document.port.status_change_query_repository import (
    StatusChangeDocumentQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.query import (
    GetStatusChangeDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.dto import (
    GetStatusChangeDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.query import (
    ListStatusChangeDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.dto import (
    ListStatusChangeDocumentsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class StatusChangeDocumentReadService:
    """Дополняет собственные проекции публичными именами компаний."""

    def __init__(
        self,
        repository: StatusChangeDocumentQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты общего UoW."""
        self._repository, self._owners = repository, owners

    async def get(
        self, query: GetStatusChangeDocumentQuery
    ) -> GetStatusChangeDocumentResultDTO:
        """Читает карточку либо сообщает об отсутствии изменения состояния."""
        result = await self._repository.get(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ изменения состояния не найден.")
        owner = await self._owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner is not None else None)

    async def list(
        self, query: ListStatusChangeDocumentsQuery
    ) -> ListStatusChangeDocumentsResultDTO:
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
