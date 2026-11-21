from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.domain.stock_execution.return_origin_snapshot import (
    StockReturnOriginSnapshot,
    StockReturnUsageSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as E,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel as Line,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_return_line import (
    StockExecutionReturnLineModel as Link,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel as Document,
)
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel as Posting,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_origin_mapper import (
    ReturnOriginMapper,
)


class SqlAlchemyReturnOriginRepository:
    """Загружает бизнес-основание на общей сессии, не изменяя исходное исполнение."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает tenant-сессию внешнего UoW."""
        self._session = session

    async def get(
        self, identifier: StockExecutionIdVO, *, lock: bool
    ) -> StockReturnOriginSnapshot | None:
        """При проведении блокирует исходный корень до чтения накопленных возвратов."""
        statement = (
            select(E)
            .where(E.id == identifier.uuid)
            .execution_options(populate_existing=True)
        )
        if lock:
            # NO KEY UPDATE сериализует лимит, сохраняя совместимость с FK KEY SHARE при создании черновика.
            statement = statement.with_for_update(key_share=True)
        execution = (await self._session.scalars(statement)).one_or_none()
        if execution is None:
            return None
        document = (
            await self._session.scalars(
                select(Document).where(Document.id == execution.document_id)
            )
        ).one()
        posting = (
            await self._session.scalars(
                select(Posting).where(
                    Posting.execution_id == execution.id,
                    Posting.reversal_of_id.is_(None),
                )
            )
        ).one_or_none()
        compensated = (
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(Posting)
                    .where(Posting.reversal_of_id == posting.id)
                )
            ).scalar_one()
            > 0
            if posting
            else False
        )
        lines = (
            await self._session.scalars(
                select(Line)
                .where(Line.execution_id == execution.id)
                .order_by(Line.position, Line.id)
            )
        ).all()
        return ReturnOriginMapper.to_snapshot(
            execution, document, posting, lines, compensated
        )

    async def usage(
        self, identifier: StockExecutionIdVO
    ) -> tuple[StockReturnUsageSnapshot, ...]:
        """Читает общий лимит всех проведённых возвратов, включая собственные записи общей транзакции."""
        actual = aliased(Line)
        statement = (
            select(Line.id, func.coalesce(func.sum(actual.quantity), Decimal(0)))
            .outerjoin(Link, Link.origin_execution_line_id == Line.id)
            .outerjoin(actual, actual.id == Link.execution_line_id)
            .where(Line.execution_id == identifier.uuid)
            .group_by(Line.id)
            .order_by(Line.id)
        )
        rows = (await self._session.execute(statement)).all()
        return tuple(
            StockReturnUsageSnapshot(
                StockExecutionLineIdVO(identifier), QuantityVO(quantity)
            )
            for identifier, quantity in rows
        )
