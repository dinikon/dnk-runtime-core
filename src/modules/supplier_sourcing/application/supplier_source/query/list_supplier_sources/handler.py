from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from dataclasses import replace
from src.modules.supplier_sourcing.application.supplier_source.port.query_repository import (
    SupplierSourceQueryRepositoryProtocol,
)
from src.modules.supplier_sourcing.application.supplier_source.port.supplier_reference import (
    SupplierReferencePort,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.query import (
    ListSupplierSourcesQuery,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.dto import (
    ListSupplierSourcesResultDTO,
)


class ListSupplierSourcesHandler:
    """Читает страницу и дополняет её актуальными названиями CRM одним пакетом."""

    def __init__(
        self,
        repository: SupplierSourceQueryRepositoryProtocol,
        suppliers: SupplierReferencePort,
    ) -> None:
        """Принимает read-порты общего tenant-контекста."""
        self._repository = repository
        self._suppliers = suppliers

    async def execute(
        self, query: ListSupplierSourcesQuery
    ) -> ListSupplierSourcesResultDTO:
        """Нормализует поиск, сохраняя нулевой offset и фильтр false."""
        result = await self._repository.list(
            replace(query, search=(query.search or "").strip() or None)
        )
        keys = tuple(
            SupplierReferenceVO.from_value(
                item.supplier_model_key.value, item.supplier_id
            )
            for item in result.items
        )
        suppliers = await self._suppliers.get_many(tuple(dict.fromkeys(keys)))
        return replace(
            result,
            items=tuple(
                replace(
                    item,
                    supplier_name=suppliers[key].name if key in suppliers else None,
                )
                for item, key in zip(result.items, keys, strict=True)
            ),
        )
