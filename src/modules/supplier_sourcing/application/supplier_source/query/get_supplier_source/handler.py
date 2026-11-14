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
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.query import (
    GetSupplierSourceQuery,
)
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.dto import (
    GetSupplierSourceResultDTO,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierSourceNotFoundError,
)


class GetSupplierSourceHandler:
    """Собирает карточку из собственной проекции и публичной ссылки CRM."""

    def __init__(
        self,
        repository: SupplierSourceQueryRepositoryProtocol,
        suppliers: SupplierReferencePort,
    ) -> None:
        """Принимает read-порты текущего tenant."""
        self._repository = repository
        self._suppliers = suppliers

    async def execute(
        self, query: GetSupplierSourceQuery
    ) -> GetSupplierSourceResultDTO:
        """Возвращает карточку без восстановления агрегата."""
        result = await self._repository.get_details(query)
        if result is None:
            raise SupplierSourceNotFoundError("Источник поставщика не найден.")
        supplier = await self._suppliers.get(
            SupplierReferenceVO.from_value(
                result.supplier_model_key.value, result.supplier_id
            )
        )
        return replace(
            result, supplier_name=supplier.name if supplier is not None else None
        )
