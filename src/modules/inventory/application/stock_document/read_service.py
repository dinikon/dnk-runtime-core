from dataclasses import replace
from src.modules.inventory.application.stock_document.port.query_repository import (
    ReceiptDocumentQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.query import (
    GetReceiptDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.dto import (
    GetReceiptDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.query import (
    ListReceiptDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.dto import (
    ListReceiptDocumentsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class ReceiptDocumentReadService:
    """Дополняет собственные проекции публичными именами компаний."""

    def __init__(
        self,
        repository: ReceiptDocumentQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты общего UoW."""
        self._repository, self._owners = repository, owners

    async def get(self, query: GetReceiptDocumentQuery) -> GetReceiptDocumentResultDTO:
        """Читает карточку либо сообщает об отсутствии поступления."""
        result = await self._repository.get(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ поступления не найден.")
        owner = await self._owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner is not None else None)

    async def list(
        self, query: ListReceiptDocumentsQuery
    ) -> ListReceiptDocumentsResultDTO:
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
