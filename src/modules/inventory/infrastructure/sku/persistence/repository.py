from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.sku.aggregate import Sku
from src.modules.inventory.domain.sku.error import (
    SkuCodeAlreadyExistsError,
    SkuIdentifierAlreadyExistsError,
)
from src.modules.inventory.infrastructure.persistence.models.sku import SkuModel
from src.modules.inventory.infrastructure.sku.persistence.mapper import SkuMapper


class SqlAlchemySkuRepository:
    """Запись агрегата; уникальность обеспечивает БД, включая конкурентные запросы."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, sku: Sku) -> None:
        """Вставляет SKU в общую транзакцию; неожиданные ошибки не маскирует."""
        try:
            await self._session.execute(
                insert(SkuModel).values(SkuMapper.to_insert_values(sku))
            )
        except IntegrityError as exc:
            original = exc.orig
            cause = original.__cause__
            constraint = getattr(original, "constraint_name", None) or getattr(
                cause,
                "constraint_name",
                None,
            )
            if getattr(original, "sqlstate", None) == "23505":
                if constraint == "uq_skus_code":
                    raise SkuCodeAlreadyExistsError("SKU code already exists.") from exc
                if constraint == "pk_skus":
                    raise SkuIdentifierAlreadyExistsError(
                        "SKU identifier already exists."
                    ) from exc
            raise
