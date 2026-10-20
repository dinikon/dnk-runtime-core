from src.modules.catalog.application.catalog_item.query.validate_catalog_draft.query import (
    ValidateCatalogDraftQuery,
)
from src.modules.catalog.application.catalog_item.query.validate_catalog_draft.dto import (
    ValidateCatalogDraftResultDTO,
)

from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.domain.error import CatalogError


class ValidateCatalogDraftHandler:
    """Проверяет вход нового Draft без сохранения или вызова write handler."""

    def __init__(self, drafts: CatalogItemCreationService) -> None:
        """Получает общий сервис проверки правил Catalog."""
        self.drafts = drafts

    async def execute(
        self, query: ValidateCatalogDraftQuery
    ) -> ValidateCatalogDraftResultDTO:
        """Возвращает ошибки полей; transient новый агрегат никогда не записывается."""
        try:
            item = await self.drafts.prepare(
                query.tenant_id, query.actor_id, query.values
            )
        except CatalogError as error:
            return ValidateCatalogDraftResultDTO(
                tuple((field, str(error)) for field in error.fields or ("draft",))
            )
        return ValidateCatalogDraftResultDTO((), item.stock.effective_status().value)
