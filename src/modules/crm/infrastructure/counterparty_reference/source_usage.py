from uuid import UUID
from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey
from src.modules.supplier_sourcing.application.supplier_source.port.supplier_usage import (
    SupplierSourceUsageProtocol,
)


class SupplierSourceCounterpartyUsageAdapter:
    """Переводит публичную проверку Supplier Sourcing в порт CRM."""

    def __init__(self, sources: SupplierSourceUsageProtocol) -> None:
        """Принимает публичный порт, без чужих ORM-моделей."""
        self._sources = sources

    async def is_used(self, model_key: CounterpartyModelKey, record_id: UUID) -> bool:
        """Проверяет оба компонента ссылки на контрагента."""
        return await self._sources.is_supplier_used(model_key.value, record_id)
