from typing import Protocol
from uuid import UUID


class SupplierSourceUsageProtocol(Protocol):
    """Публичный контракт проверки ссылок на контрагента поставщика."""

    async def is_supplier_used(self, model_key: str, supplier_id: UUID) -> bool:
        """Учитывает активные и деактивированные источники."""
        ...
