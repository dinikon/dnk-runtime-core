from uuid import UUID
from src.modules.crm.application.counterparty_reference.service import (
    CounterpartyReferenceService,
)
from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReference,
)


class CrmStockOwnerReference:
    """Адаптирует публичный контракт компаний CRM без чужих ORM-моделей."""

    def __init__(self, service: CounterpartyReferenceService) -> None:
        """Принимает публичный Application-сервис общего UoW."""
        self._service = service

    async def get(
        self, identifier: UUID, *, lock: bool = False
    ) -> StockOwnerReference | None:
        """Не выполняет поиск контакта при отсутствии компании с этим UUID."""
        item = await self._service.get(
            CounterpartyModelKey.COMPANY, identifier, lock=lock
        )
        return (
            StockOwnerReference(item.id, item.display_name)
            if item is not None
            else None
        )

    async def get_many(
        self, identifiers: tuple[UUID, ...]
    ) -> dict[UUID, StockOwnerReference]:
        """Пакетно читает только компании."""
        items = await self._service.get_many(
            tuple(
                (CounterpartyModelKey.COMPANY, identifier)
                for identifier in dict.fromkeys(identifiers)
            )
        )
        return {
            identifier: StockOwnerReference(item.id, item.display_name)
            for (_, identifier), item in items.items()
        }
