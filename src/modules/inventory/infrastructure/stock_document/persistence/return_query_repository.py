from src.modules.inventory.infrastructure.persistence.models.stock_document_return_line import (
    StockDocumentReturnLineModel as ReturnLink,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_return import (
    StockDocumentReturnModel as ReturnDetails,
)
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
from src.modules.inventory.infrastructure.stock_document.persistence.return_query_mapper import (
    ReturnDocumentQueryMapper,
)
from src.modules.inventory.application.stock_document.query.get_return_document.query import (
    GetReturnDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_return_document.dto import (
    GetReturnDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.query import (
    ListReturnDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.dto import (
    ListReturnDocumentsResultDTO,
)


class SqlAlchemyReturnDocumentQueryRepository:
    """Читает возвраты без загрузки Domain и без чужих ORM-моделей."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию выбранного tenant."""
        self._session = session

    async def get(
        self, query: GetReturnDocumentQuery
    ) -> GetReturnDocumentResultDTO | None:
        """Читает реквизиты и nullable-строки одним согласованным SELECT."""
        statement = (
            select(
                Document,
                WarehouseModel,
                Nullable(Line),
                Nullable(Line.planned_qty - Line.executed_qty),
                ReturnDetails,
                Nullable(ReturnLink.origin_execution_line_id),
            )
            .join(WarehouseModel, WarehouseModel.id == Document.warehouse_id)
            .join(ReturnDetails, ReturnDetails.document_id == Document.id)
            .outerjoin(Line, Line.document_id == Document.id)
            .outerjoin(ReturnLink, ReturnLink.document_line_id == Line.id)
            .where(
                Document.id == query.document_id,
                Document.operation_type == "RETURN",
            )
            .order_by(Line.position, Line.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return None
        return ReturnDocumentQueryMapper.to_details(
            rows[0][0],
            rows[0][1],
            rows[0][4],
            tuple(
                (line, remaining, origin_line_id)
                for _, _, line, remaining, _, origin_line_id in rows
                if line is not None
                and remaining is not None
                and origin_line_id is not None
            ),
        )

    async def list(
        self, query: ListReturnDocumentsQuery
    ) -> ListReturnDocumentsResultDTO:
        """Не размножает документы при поиске SKU и использует общие фильтры страницы/count."""
        conditions: list[ColumnElement[bool]] = [Document.operation_type == "RETURN"]
        if query.origin_execution_id is not None:
            conditions.append(
                ReturnDetails.origin_execution_id == query.origin_execution_id
            )
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
                    ReturnDetails.reason.icontains(query.search, autoescape=True),
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
                select(func.count())
                .select_from(Document)
                .join(ReturnDetails, ReturnDetails.document_id == Document.id)
                .where(*filters)
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
            select(Document, WarehouseModel, count, ReturnDetails)
            .join(WarehouseModel, WarehouseModel.id == Document.warehouse_id)
            .join(ReturnDetails, ReturnDetails.document_id == Document.id)
            .where(*filters)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        return ListReturnDocumentsResultDTO(
            items=tuple(
                ReturnDocumentQueryMapper.to_list_item(
                    model, warehouse, details, line_count
                )
                for model, warehouse, line_count, details in rows
            ),
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
