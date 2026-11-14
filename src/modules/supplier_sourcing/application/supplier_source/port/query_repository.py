from typing import Protocol
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.query import (
    GetSupplierSourceQuery,
)
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.dto import (
    GetSupplierSourceResultDTO,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.query import (
    ListSupplierSourcesQuery,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.dto import (
    ListSupplierSourcesResultDTO,
)


class SupplierSourceQueryRepositoryProtocol(Protocol):
    """Читает собственные проекции источников без чужих ORM-моделей."""

    async def get_details(
        self, query: GetSupplierSourceQuery
    ) -> GetSupplierSourceResultDTO | None:
        """Возвращает карточку либо отсутствие источника."""
        ...

    async def list(
        self, query: ListSupplierSourcesQuery
    ) -> ListSupplierSourcesResultDTO:
        """Возвращает страницу и согласованный total."""
        ...
