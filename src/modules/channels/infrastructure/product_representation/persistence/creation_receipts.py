from dataclasses import asdict
from datetime import datetime
from uuid import UUID
from sqlalchemy import select, insert, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.product_representation.contracts import (
    CatalogCreationReceiptDTO,
)
from src.modules.channels.infrastructure.persistence.models.catalog_creation_request import (
    CatalogCreationRequestModel as R,
)


class SqlAlchemyCatalogCreationReceipts:
    """Сериализует intent и сохраняет receipt вместе с новым товаром."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant-сессию."""
        self.session = session

    async def lock_key(self, tenant_id: UUID, request_key: UUID) -> None:
        """Предотвращает одинаковые ключи для разных источников и входов."""
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"channels:create:{tenant_id}:{request_key}"},
        )

    async def get(self, request_key: UUID) -> CatalogCreationReceiptDTO | None:
        """Возвращает immutable сохранённый результат до проверки свежести source."""
        row = (
            (
                await self.session.execute(
                    select(R.__table__).where(R.request_key == request_key)
                )
            )
            .mappings()
            .one_or_none()
        )
        return (
            CatalogCreationReceiptDTO(
                **{
                    name: row[name]
                    for name in CatalogCreationReceiptDTO.__dataclass_fields__
                }
            )
            if row
            else None
        )

    async def add(
        self, receipt: CatalogCreationReceiptDTO, actor_id: UUID, now: datetime
    ) -> None:
        """Записывает только завершённый результат общей транзакции."""
        await self.session.execute(
            insert(R).values(**asdict(receipt), actor_id=actor_id, created_at=now)
        )
