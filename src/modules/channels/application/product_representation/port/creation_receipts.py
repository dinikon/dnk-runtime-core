from typing import Protocol
from uuid import UUID
from datetime import datetime
from src.modules.channels.application.product_representation.contracts import (
    CatalogCreationReceiptDTO,
)


class CatalogCreationReceiptsPort(Protocol):
    """Хранит идемпотентные результаты одного create+bind на общем UoW."""

    async def lock_key(self, tenant_id: UUID, request_key: UUID) -> None:
        """Сериализует одинаковый key в разных публикациях до проверки входа."""
        ...

    async def get(self, request_key: UUID) -> CatalogCreationReceiptDTO | None:
        """Читает завершённый результат до текущей observed revision."""
        ...

    async def add(
        self, receipt: CatalogCreationReceiptDTO, actor_id: UUID, now: datetime
    ) -> None:
        """Сохраняет результат в транзакции товара и привязки."""
        ...
