from typing import cast
from uuid import UUID
from sqlalchemy import select, or_, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReference,
)
from src.modules.catalog.application.catalog_item.port.publication_reader import (
    CatalogPublicationSubject,
    CatalogPublicationSelectionError,
    CatalogPublicationFamilyNotFoundError,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value import (
    CatalogItemContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)


class SqlAlchemyCatalogPublicationReader:
    """Читает только выбранные строки и локализованные подписи внутри Catalog."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует общую tenant-сессию без владения транзакцией."""
        self._session = session

    async def _titles(
        self, identifiers: tuple[UUID, ...], locale: str
    ) -> dict[UUID, str | None]:
        """Сохраняет отличие отсутствующей строки от явного clear у варианта."""
        if not identifiers:
            return {}
        value = CatalogItemContentValueModel.__table__
        rows = (
            await self._session.execute(
                select(value.c.catalog_item_id, value.c.value)
                .join(ContentBlockModel, ContentBlockModel.id == value.c.block_id)
                .where(
                    value.c.catalog_item_id.in_(identifiers),
                    value.c.locale == locale,
                    ContentBlockModel.code == "title",
                )
            )
        ).all()
        return {cast(UUID, row[0]): cast(str | None, row[1]) for row in rows}

    async def read_many(
        self, references: tuple[CatalogCalculationReference, ...], locale: str
    ) -> tuple[CatalogPublicationSubject, ...]:
        """Проверяет роли и принадлежность пакетно; не загружает соседние варианты."""
        if len(references) > 100:
            raise CatalogPublicationSelectionError("Допустимо не более 100 позиций.")
        identifiers = tuple(
            {
                identifier
                for ref in references
                for identifier in (ref.item_id, ref.variant_id)
                if identifier is not None
            }
        )
        if not identifiers:
            return ()
        table = CatalogItemModel.__table__
        rows = (
            await self._session.execute(
                select(
                    table.c.id,
                    table.c.parent_id,
                    table.c.kind,
                    table.c.status,
                    table.c.sku,
                ).where(table.c.id.in_(identifiers))
            )
        ).mappings()
        indexed = {row["id"]: row for row in rows}
        titles = await self._titles(identifiers, locale)
        result: list[CatalogPublicationSubject] = []
        for ref in references:
            root = indexed.get(ref.item_id)
            own = indexed.get(ref.variant_id or ref.item_id)
            if root is None or own is None or root["parent_id"] is not None:
                continue
            valid = (
                root["kind"] == "simple"
                if ref.variant_id is None
                else root["kind"] == "variable"
                and own["kind"] == "variant"
                and own["parent_id"] == ref.item_id
            )
            if not valid:
                continue
            title = (
                titles.get(own["id"]) if own["id"] in titles else titles.get(root["id"])
            )
            result.append(
                CatalogPublicationSubject(
                    ref,
                    cast(str, own["kind"]),
                    cast(str | None, own["sku"]),
                    title,
                    titles.get(root["id"]) if ref.variant_id else None,
                    root["status"] != "archived" and own["status"] != "archived",
                )
            )
        return tuple(result)

    async def search_ids(self, search: str, locale: str) -> tuple[UUID, ...]:
        """Ищет SKU/названия на сервере и отдаёт минимальные IDs без чужого JOIN."""
        item = CatalogItemModel.__table__
        value = CatalogItemContentValueModel.__table__
        title = (
            select(value.c.catalog_item_id)
            .join(ContentBlockModel, ContentBlockModel.id == value.c.block_id)
            .where(
                value.c.locale == locale,
                ContentBlockModel.code == "title",
                value.c.value.icontains(search, autoescape=True),
            )
        )
        return tuple(
            (
                await self._session.scalars(
                    select(item.c.id).where(
                        or_(
                            item.c.sku.icontains(search, autoescape=True),
                            item.c.id.in_(title),
                        )
                    )
                )
            ).all()
        )

    async def variant_selection(
        self, root_id: UUID, locale: str
    ) -> tuple[CatalogPublicationSubject, ...]:
        """Читает фиксированный набор ID и общий размер в одном SQL snapshot."""
        root = CatalogItemModel.__table__.alias("selection_root")
        child = CatalogItemModel.__table__.alias("selection_child")
        rows = (
            await self._session.execute(
                select(
                    root.c.status,
                    child.c.id,
                    func.count(child.c.id).over().label("total"),
                )
                .select_from(
                    root.outerjoin(
                        child,
                        and_(
                            child.c.parent_id == root.c.id,
                            child.c.kind == "variant",
                            child.c.status != "archived",
                        ),
                    )
                )
                .where(
                    root.c.id == root_id,
                    root.c.kind == "variable",
                    root.c.parent_id.is_(None),
                )
                .order_by(child.c.id)
                .limit(101)
            )
        ).all()
        if not rows or rows[0][0] == "archived":
            raise CatalogPublicationFamilyNotFoundError("Семейство недоступно.")
        if rows[0][2] > 100:
            raise CatalogPublicationSelectionError(
                "В семействе больше 100 вариантов. Выберите позиции вручную."
            )
        references = tuple(
            CatalogCalculationReference(root_id, cast(UUID, row[1]))
            for row in rows
            if row[1] is not None
        )
        # Набор ID зафиксирован: новые варианты между чтениями сюда не попадут.
        subjects = await self.read_many(references, locale)
        if len(subjects) != len(references) or any(not s.available for s in subjects):
            raise CatalogPublicationFamilyNotFoundError(
                "Состав вариантов изменён. Обновите выбор."
            )
        return subjects
