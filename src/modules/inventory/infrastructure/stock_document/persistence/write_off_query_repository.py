from sqlalchemy import select, func, Nullable, or_
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel as Document,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel as Line,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.write_off_query_mapper import (
    WriteOffDocumentQueryMapper,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.query import (
    GetWriteOffDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.dto import (
    GetWriteOffDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.query import (
    ListWriteOffDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.dto import (
    ListWriteOffDocumentsResultDTO,
)


class SqlAlchemyWriteOffDocumentQueryRepository:
    """Читает списания без загрузки Domain и без чужих ORM-моделей."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию выбранного tenant."""
        self._session = session

    async def get(
        self, query: GetWriteOffDocumentQuery
    ) -> GetWriteOffDocumentResultDTO | None:
        """Читает реквизиты и nullable-строки одним согласованным SELECT."""
        statement = (
            select(
                Document,
                WarehouseModel,
                Nullable(Line),
                Nullable(Line.planned_qty - Line.executed_qty),
            )
            .join(WarehouseModel, WarehouseModel.id == Document.warehouse_id)
            .outerjoin(Line, Line.document_id == Document.id)
            .where(
                Document.id == query.document_id, Document.operation_type == "WRITE_OFF"
            )
            .order_by(Line.position, Line.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return None
        return WriteOffDocumentQueryMapper.to_details(
            rows[0][0],
            rows[0][1],
            tuple(
                (line, remaining)
                for _, _, line, remaining in rows
                if line is not None and remaining is not None
            ),
        )

    async def list(
        self, query: ListWriteOffDocumentsQuery
    ) -> ListWriteOffDocumentsResultDTO:
        """Не размножает документы при поиске SKU и использует общие фильтры страницы/count."""
        conditions: list[ColumnElement[bool]] = [Document.operation_type == "WRITE_OFF"]
        if query.status is not None:
            conditions.append(Document.status == query.status.value)
        if query.warehouse_id is not None:
            conditions.append(Document.warehouse_id == query.warehouse_id)
        if query.owner_id is not None:
            conditions.append(Document.owner_id == query.owner_id)
        if query.created_from is not None:
            conditions.append(Document.created_at >= query.created_from)
        if query.created_to is not None:
            conditions.append(Document.created_at <= query.created_to)
        if query.search is not None:
            conditions.append(
                or_(
                    Document.write_off_reason.icontains(query.search, autoescape=True),
                    select(Line.id)
                    .where(
                        Line.document_id == Document.id,
                        Line.sku.contains(query.search.casefold(), autoescape=True),
                    )
                    .exists(),
                )
            )
        filters = tuple(conditions)
        total = (
            await self._session.execute(
                select(func.count()).select_from(Document).where(*filters)
            )
        ).scalar_one()
        count = (
            select(func.count())
            .select_from(Line)
            .where(Line.document_id == Document.id)
            .correlate(Document)
            .scalar_subquery()
        )
        statement = (
            select(Document, WarehouseModel, count)
            .join(WarehouseModel, WarehouseModel.id == Document.warehouse_id)
            .where(*filters)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        return ListWriteOffDocumentsResultDTO(
            items=tuple(
                WriteOffDocumentQueryMapper.to_list_item(model, warehouse, line_count)
                for model, warehouse, line_count in rows
            ),
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
