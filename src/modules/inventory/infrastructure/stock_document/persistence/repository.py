from src.modules.inventory.infrastructure.persistence.models.stock_document_return import (
    StockDocumentReturnModel as ReturnDetails,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_return_line import (
    StockDocumentReturnLineModel as ReturnLine,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_status_change import (
    StockDocumentStatusChangeModel as StatusDetails,
)
from collections.abc import Sequence
from uuid import UUID
from sqlalchemy import insert, select, update, delete
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentNotFoundError,
    StaleStockDocumentVersionError,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.mapper import (
    StockDocumentMapper,
)


class SqlAlchemyStockDocumentRepository:
    """Сохраняет новый документ и дочерние строки в общей tenant-транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW."""
        self._session = session

    async def add(self, document: StockDocument) -> None:
        """Вставляет корень и строки без upsert и самостоятельного commit."""
        lines = StockDocumentMapper.to_line_insert_values(document)
        await self._session.execute(
            insert(StockDocumentModel).values(
                StockDocumentMapper.to_insert_values(document)
            )
        )
        if document.status_change_details is not None:
            await self._session.execute(
                insert(StatusDetails).values(
                    StockDocumentMapper.status_change_values(document)
                )
            )
        if lines:
            await self._session.execute(insert(StockDocumentLineModel), lines)
        if document.return_details is not None:
            await self._session.execute(
                insert(ReturnDetails).values(
                    StockDocumentMapper.return_values(document)
                )
            )
            links = StockDocumentMapper.return_line_values(document)
            if links:
                await self._session.execute(insert(ReturnLine), links)

    async def get_for_update(
        self, identifier: StockDocumentIdVO
    ) -> StockDocument | None:
        """Перечитывает заблокированный корень и детей без отдельного репозитория строк."""
        statement = (
            select(StockDocumentModel)
            .where(StockDocumentModel.id == identifier.uuid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        children = await self._read_lines(model.id)
        details = (
            await self._session.scalars(
                select(StatusDetails)
                .where(StatusDetails.document_id == model.id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        return_details = (
            await self._session.scalars(
                select(ReturnDetails)
                .where(ReturnDetails.document_id == model.id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        return_lines = (
            await self._session.scalars(
                select(ReturnLine)
                .join(
                    StockDocumentLineModel,
                    StockDocumentLineModel.id == ReturnLine.document_line_id,
                )
                .where(StockDocumentLineModel.document_id == model.id)
            )
        ).all()
        return StockDocumentMapper.to_domain(
            model, children, details, return_details, return_lines
        )

    async def _read_lines(self, identifier: UUID) -> Sequence[StockDocumentLineModel]:
        """Читает упорядоченный собственный состав после блокировки корня."""
        statement = (
            select(StockDocumentLineModel)
            .where(StockDocumentLineModel.document_id == identifier)
            .order_by(StockDocumentLineModel.position, StockDocumentLineModel.id)
            .execution_options(populate_existing=True)
        )
        return (await self._session.scalars(statement)).all()

    async def save(self, document: StockDocument, *, expected_version: int) -> None:
        """Обновляет корень и разницу строк атомарно, сохраняя идентичность неизменённых детей."""
        values = StockDocumentMapper.to_line_insert_values(document)
        statement = (
            update(StockDocumentModel)
            .where(
                StockDocumentModel.id == document.id.uuid,
                StockDocumentModel.version == expected_version,
            )
            .values(StockDocumentMapper.to_update_values(document))
            .returning(StockDocumentModel.id)
            .execution_options(synchronize_session=False)
        )
        if await self._session.scalar(statement) is None:
            current = await self._session.scalar(
                select(StockDocumentModel.version).where(
                    StockDocumentModel.id == document.id.uuid
                )
            )
            if current is None:
                raise StockDocumentNotFoundError("Документ поступления не найден.")
            raise StaleStockDocumentVersionError(
                "Версия документа изменилась при сохранении.",
                expected_version=expected_version,
                actual_version=current,
            )
        if document.status_change_details is not None:
            details_statement = (
                update(StatusDetails)
                .where(StatusDetails.document_id == document.id.uuid)
                .values(StockDocumentMapper.status_change_values(document))
                .returning(StatusDetails.document_id)
            )
            if await self._session.scalar(details_statement) is None:
                raise RuntimeError(
                    "Сохранённый STATUS_CHANGE не содержит собственных параметров."
                )
        children = await self._read_lines(document.id.uuid)
        existing = {line.id: line for line in children}
        retained = {line.id.uuid for line in document.lines} & existing.keys()
        removed = existing.keys() - retained
        if removed:
            await self._session.execute(
                delete(ReturnLine).where(ReturnLine.document_line_id.in_(removed))
            )
            await self._session.execute(
                delete(StockDocumentLineModel)
                .where(
                    StockDocumentLineModel.document_id == document.id.uuid,
                    StockDocumentLineModel.id.in_(removed),
                )
                .execution_options(synchronize_session=False)
            )
        reindex = any(
            existing[line.id.uuid].position != position
            for position, line in enumerate(document.lines)
            if line.id.uuid in retained
        )
        if reindex:
            # Временный непересекающийся диапазон защищает UNIQUE(document_id, position).
            shift = (
                max((line.position for line in children), default=0) + len(values) + 1
            )
            await self._session.execute(
                update(StockDocumentLineModel)
                .where(
                    StockDocumentLineModel.document_id == document.id.uuid,
                    StockDocumentLineModel.id.in_(retained),
                )
                .values(position=StockDocumentLineModel.position + shift)
                .execution_options(synchronize_session=False)
            )
        added = []
        for position, (line, row) in enumerate(
            zip(document.lines, values, strict=True)
        ):
            model = existing.get(line.id.uuid)
            if model is None:
                added.append(row)
            elif reindex or not StockDocumentMapper.line_matches(model, line, position):
                await self._session.execute(
                    update(StockDocumentLineModel)
                    .where(
                        StockDocumentLineModel.document_id == document.id.uuid,
                        StockDocumentLineModel.id == line.id.uuid,
                    )
                    .values(row)
                    .execution_options(synchronize_session=False)
                )
        if added:
            await self._session.execute(insert(StockDocumentLineModel), added)

        if document.return_details is not None:
            await self._session.execute(
                update(ReturnDetails)
                .where(ReturnDetails.document_id == document.id.uuid)
                .values(reason=document.return_details.reason.value)
            )
            new_links = [
                link
                for link in StockDocumentMapper.return_line_values(document)
                if link["document_line_id"] not in retained
            ]
            if new_links:
                await self._session.execute(insert(ReturnLine), new_links)

    async def get(self, identifier: StockDocumentIdVO) -> StockDocument | None:
        """Перечитывает прочитанный корень и детей без отдельного репозитория строк."""
        statement = (
            select(StockDocumentModel)
            .where(StockDocumentModel.id == identifier.uuid)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        children = await self._read_lines(model.id)
        details = (
            await self._session.scalars(
                select(StatusDetails)
                .where(StatusDetails.document_id == model.id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        return_details = (
            await self._session.scalars(
                select(ReturnDetails)
                .where(ReturnDetails.document_id == model.id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        return_lines = (
            await self._session.scalars(
                select(ReturnLine)
                .join(
                    StockDocumentLineModel,
                    StockDocumentLineModel.id == ReturnLine.document_line_id,
                )
                .where(StockDocumentLineModel.document_id == model.id)
            )
        ).all()
        return StockDocumentMapper.to_domain(
            model, children, details, return_details, return_lines
        )
