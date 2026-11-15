from dataclasses import replace
from src.modules.inventory.application.stock_document.port.issue_query_repository import (
    IssueDocumentQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_document.query.get_issue_document.query import (
    GetIssueDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_issue_document.dto import (
    GetIssueDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.query import (
    ListIssueDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.dto import (
    ListIssueDocumentsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class IssueDocumentReadService:
    """Дополняет собственные проекции публичными именами компаний."""

    def __init__(
        self,
        repository: IssueDocumentQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты общего UoW."""
        self._repository, self._owners = repository, owners

    async def get(self, query: GetIssueDocumentQuery) -> GetIssueDocumentResultDTO:
        """Читает карточку либо сообщает об отсутствии расхода."""
        result = await self._repository.get(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ расхода не найден.")
        owner = await self._owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner is not None else None)

    async def list(self, query: ListIssueDocumentsQuery) -> ListIssueDocumentsResultDTO:
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
