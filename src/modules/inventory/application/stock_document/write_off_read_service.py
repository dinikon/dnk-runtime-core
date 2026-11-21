from dataclasses import replace
from src.modules.inventory.application.stock_document.port.write_off_query_repository import (
    WriteOffDocumentQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.query import (
    GetWriteOffDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.dto import (
    GetWriteOffDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.query import (
    ListWriteOffDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.dto import (
    ListWriteOffDocumentsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class WriteOffDocumentReadService:
    """Дополняет собственные проекции публичными именами компаний."""

    def __init__(
        self,
        repository: WriteOffDocumentQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты общего UoW."""
        self._repository, self._owners = repository, owners

    async def get(
        self, query: GetWriteOffDocumentQuery
    ) -> GetWriteOffDocumentResultDTO:
        """Читает карточку либо сообщает об отсутствии списания."""
        result = await self._repository.get(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ списания не найден.")
        owner = await self._owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner is not None else None)

    async def list(
        self, query: ListWriteOffDocumentsQuery
    ) -> ListWriteOffDocumentsResultDTO:
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
