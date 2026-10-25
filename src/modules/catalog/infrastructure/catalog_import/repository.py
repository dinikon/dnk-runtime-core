from dataclasses import asdict
from datetime import timedelta
from src.config import dnk_config
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from uuid import UUID, uuid5
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.catalog_import.aggregate import CatalogImport, EXECUTING
from src.modules.catalog.domain.error import CatalogNotFoundError, CatalogConflictError
from src.modules.catalog.infrastructure.persistence.models.catalog_import import (
    CatalogImportModel as Imports,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_import_row import (
    CatalogImportRowModel as Rows,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.catalog.infrastructure.catalog_import.mapper import (
    CatalogImportMapper,
    CatalogImportQueryMapper,
    configuration_from_values,
)
from src.modules.catalog.application.catalog_import.contracts import (
    SourceRecord,
    ImportRowResult,
)
from src.modules.catalog.application.catalog_import.read_models import ImportAnalysisDTO
from src.modules.catalog.application.catalog_import.query.get_catalog_import.dto import (
    GetCatalogImportResultDTO,
)
from src.modules.catalog.application.catalog_import.query.list_catalog_imports.dto import (
    ListCatalogImportsResultDTO,
)
from src.modules.catalog.application.catalog_import.query.list_catalog_import_rows.dto import (
    ListCatalogImportRowsResultDTO,
)


class SqlAlchemyCatalogImportRepository:
    """Хранит агрегат в привязанной tenant-сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего UoW."""
        self.session = session

    async def get(self, identifier: EntityIdVO, *, lock: bool = False) -> CatalogImport:
        """Загружает только состояние агрегата."""
        statement = select(Imports.__table__).where(Imports.id == identifier.uuid)
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).mappings().one_or_none()
        if row is None:
            raise CatalogNotFoundError("Импорт не найден.")
        return CatalogImportMapper.to_domain(row)

    async def by_key(self, key: str) -> CatalogImport | None:
        """Возвращает исходный запуск повторённого запроса."""
        row = (
            (
                await self.session.execute(
                    select(Imports.__table__).where(Imports.idempotency_key == key)
                )
            )
            .mappings()
            .one_or_none()
        )
        return CatalogImportMapper.to_domain(row) if row else None

    async def save(self, entity: CatalogImport) -> None:
        """Вставляет либо обновляет агрегат без самостоятельного commit."""
        values = CatalogImportMapper.to_values(entity)
        statement = insert(Imports).values(**values)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[Imports.id],
                set_={k: v for k, v in values.items() if k != "id"},
            )
        )

    async def lock_lane(self) -> None:
        """Блокирует запуск только текущей tenant-схемы."""
        options = self.session.get_bind().get_execution_options()
        schema = str(options.get("schema_translate_map", {}))
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": schema + ":catalog-import"},
        )

    async def count_executing(self, exclude: EntityIdVO) -> int:
        """Считает активные запуски этой схемы после получения lock_lane."""
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(Imports)
                .where(Imports.id != exclude.uuid, Imports.status.in_(EXECUTING))
            )
            or 0
        )


class SqlAlchemyImportRows:
    """Сохраняет staging и результаты; не реализует инварианты товара."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую сессию без управления транзакцией."""
        self.session = session

    async def reset(self, identifier: UUID) -> None:
        """Очищает незапущенную staging-проекцию."""
        await self.session.execute(delete(Rows).where(Rows.import_id == identifier))

    async def describe(self, identifier: UUID, analysis: ImportAnalysisDTO) -> None:
        """Сохраняет только технический предпросмотр на общей сессии."""
        await self.session.execute(
            update(Imports)
            .where(Imports.id == identifier)
            .values(analysis=asdict(analysis))
        )

    async def stage(self, identifier: UUID, rows: tuple[SourceRecord, ...]) -> None:
        """Записывает ограниченную порцию; номер уникален в пределах снимка."""
        if rows:
            await self.session.execute(
                insert(Rows)
                .values(
                    [
                        dict(
                            id=uuid5(identifier, f"row:{r.number}"),
                            import_id=identifier,
                            number=r.number,
                            values=r.values,
                            outcome="pending",
                            errors=[],
                            warnings=[],
                        )
                        for r in rows
                    ]
                )
                .on_conflict_do_nothing(index_elements=[Rows.import_id, Rows.number])
            )

    async def next_row(self, identifier: UUID) -> SourceRecord | None:
        """Читает первую ещё не завершённую позицию."""
        row = (
            (
                await self.session.execute(
                    select(Rows.number, Rows.values)
                    .where(Rows.import_id == identifier, Rows.outcome == "pending")
                    .order_by(Rows.number)
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        return SourceRecord(row["number"], row["values"]) if row else None

    async def finish(self, identifier: UUID, result: ImportRowResult) -> None:
        """Пишет результат в транзакции товара и счётчиков."""
        values = asdict(result)
        number = values.pop("number")
        result = await self.session.execute(
            update(Rows)
            .where(
                Rows.import_id == identifier,
                Rows.number == number,
                Rows.outcome == "pending",
            )
            .values(**values)
        )
        if result.rowcount != 1:
            raise CatalogConflictError(
                "Запись уже обработана другим выполнением задания."
            )

    async def duplicate(self, identifier: UUID, number: int, sku: str) -> bool:
        """Учитывает SKU любой предыдущей завершённой строки, включая ошибочную."""
        return bool(
            await self.session.scalar(
                select(Rows.id)
                .where(
                    Rows.import_id == identifier, Rows.number < number, Rows.sku == sku
                )
                .limit(1)
            )
        )

    async def find_item(self, sku: str) -> UUID | None:
        """Сериализует поиск/создание одного SKU между параллельными импортами."""
        schema = str(
            self.session.get_bind()
            .get_execution_options()
            .get("schema_translate_map", {})
        )
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": schema + ":catalog-import-sku:" + sku},
        )
        return await self.session.scalar(
            select(CatalogItemModel.id).where(
                CatalogItemModel.sku == sku, CatalogItemModel.kind == "simple"
            )
        )


class SqlAlchemyImportRead:
    """Читает SQL-проекции, не загружая агрегаты и все строки."""

    def __init__(
        self,
        session: AsyncSession,
        clock: ClockPort | None = None,
        source_lifetime: timedelta | None = None,
    ) -> None:
        """Получает read-сессию внешнего UoW."""
        self.session = session
        self.clock = clock or UtcClock()
        self.source_lifetime = (
            source_lifetime
            if source_lifetime is not None
            else timedelta(days=dnk_config.CATALOG_IMPORT.source_days)
        )

    async def get(self, identifier: UUID) -> GetCatalogImportResultDTO:
        """Возвращает ограниченный предпросмотр запуска."""
        row = (
            (
                await self.session.execute(
                    select(Imports.__table__).where(Imports.id == identifier)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CatalogNotFoundError("Импорт не найден.")
        return GetCatalogImportResultDTO(
            CatalogImportQueryMapper.to_summary(
                row, now=self.clock.now(), source_lifetime=self.source_lifetime
            ),
            configuration_from_values(row["configuration"]),
            CatalogImportQueryMapper.to_analysis(row["analysis"]),
        )

    async def list(self, offset: int, limit: int) -> ListCatalogImportsResultDTO:
        """Читает страницу последних запусков."""
        rows = (
            await self.session.execute(
                select(Imports.__table__)
                .order_by(Imports.created_at.desc(), Imports.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).mappings()
        return ListCatalogImportsResultDTO(
            tuple(
                CatalogImportQueryMapper.to_summary(
                    row, now=self.clock.now(), source_lifetime=self.source_lifetime
                )
                for row in rows
            ),
            int(
                await self.session.scalar(select(func.count()).select_from(Imports))
                or 0
            ),
        )

    async def rows(
        self, identifier: UUID, outcome: str | None, offset: int, limit: int
    ) -> ListCatalogImportRowsResultDTO:
        """Читает только результаты выбранного запуска."""
        if not await self.session.scalar(
            select(Imports.id).where(Imports.id == identifier)
        ):
            raise CatalogNotFoundError("Импорт не найден.")
        filters = [Rows.import_id == identifier]
        if outcome == "warnings":
            filters.append(func.jsonb_array_length(Rows.warnings) > 0)
        elif outcome:
            filters.append(Rows.outcome == outcome)
        rows = (
            await self.session.execute(
                select(Rows.__table__)
                .where(*filters)
                .order_by(Rows.number)
                .offset(offset)
                .limit(limit)
            )
        ).mappings()
        items = tuple(
            ImportRowResult(
                r["number"],
                r["outcome"],
                r["sku"],
                r["item_id"],
                tuple(r["errors"]),
                tuple(r["warnings"]),
            )
            for r in rows
        )
        return ListCatalogImportRowsResultDTO(
            items,
            int(
                await self.session.scalar(
                    select(func.count()).select_from(Rows).where(*filters)
                )
                or 0
            ),
        )
