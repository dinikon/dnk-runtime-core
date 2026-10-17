from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product_type.query.get_default_product_type.query import (
    GetDefaultProductTypeQuery,
)
from src.modules.catalog.application.product_type.query.get_default_product_type.dto import (
    GetDefaultProductTypeResultDTO,
)
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)


class GetDefaultProductTypeHandler:
    """Возвращает фиксированный контракт контента из read порта."""

    def __init__(self, schemas: CatalogItemContentSchemaPort) -> None:
        """Получает порт схемы на общем UoW."""
        self._schemas = schemas

    async def execute(
        self, query: GetDefaultProductTypeQuery
    ) -> GetDefaultProductTypeResultDTO:
        """Отдаёт Default без возможности изменения схемы."""
        LocaleVO(query.locale)
        return GetDefaultProductTypeResultDTO(
            await self._schemas.get_default(query.locale), query.locale
        )
