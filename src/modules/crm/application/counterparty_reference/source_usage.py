from typing import Protocol
from uuid import UUID
from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey


class CounterpartySourceUsagePort(Protocol):
    """Проверяет использование составной ссылки контрагента перед удалением."""

    async def is_used(self, model_key: CounterpartyModelKey, record_id: UUID) -> bool:
        """Учитывает только точный тип и UUID контрагента."""
        ...
