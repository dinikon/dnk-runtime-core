from sqlalchemy import select, insert, update, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.error import (
    PublicationNotFoundError,
    PublicationVersionConflictError,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_version import (
    FeedPublicationVersionVO,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.infrastructure.persistence.models.publication import (
    FeedPublicationModel as Model,
)
from src.modules.feed_builder.infrastructure.publication.persistence.mapper import (
    FeedPublicationMapper,
)


class SqlAlchemyFeedPublicationRepository:
    """Хранит агрегаты на внешней tenant-сессии после блокировки Feed."""

    def __init__(self, session: AsyncSession) -> None:
        """Не открывает транзакцию и не выбирает tenant самостоятельно."""
        self._session = session

    async def find(
        self, feed_id: FeedIdVO, references: tuple[CatalogProductReferenceVO, ...]
    ) -> tuple[FeedPublication, ...]:
        """Читает существующие идентичности одним запросом, включая архив."""
        if not references:
            return ()
        rows = (
            await self._session.execute(
                select(Model.__table__).where(
                    Model.feed_id == feed_id.uuid,
                    or_(
                        *(
                            and_(
                                Model.catalog_item_id == r.catalog_item_id.uuid,
                                (
                                    Model.catalog_variant_id
                                    == r.catalog_variant_id.uuid
                                    if r.catalog_variant_id
                                    else Model.catalog_variant_id.is_(None)
                                ),
                            )
                            for r in references
                        )
                    ),
                )
            )
        ).mappings()
        return tuple(FeedPublicationMapper.to_domain(r) for r in rows)

    async def get_for_update(self, identifier: FeedPublicationIdVO) -> FeedPublication:
        """Блокирует только публикацию текущего tenant."""
        row = (
            (
                await self._session.execute(
                    select(Model.__table__)
                    .where(Model.id == identifier.uuid)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise PublicationNotFoundError("Публикация не найдена.")
        return FeedPublicationMapper.to_domain(row)

    async def add_many(self, publications: tuple[FeedPublication, ...]) -> None:
        """Вставляет ограниченный пакет одним вызовом без собственного commit."""
        if publications:
            await self._session.execute(
                insert(Model),
                [FeedPublicationMapper.to_insert_values(p) for p in publications],
            )

    async def save(
        self, publication: FeedPublication, expected_version: FeedPublicationVersionVO
    ) -> None:
        """Меняет только участие и версию, сохраняя JSON overrides без перезаписи."""
        if publication.version.value != expected_version.value + 1:
            raise PublicationVersionConflictError("Неверная новая версия.")
        result = await self._session.execute(
            update(Model)
            .where(
                Model.id == publication.id.uuid,
                Model.row_version == expected_version.value,
            )
            .values(
                status=publication.status.value,
                row_version=publication.version.value,
                updated_at=publication.updated_at,
            )
            .returning(Model.id)
        )
        if result.scalar_one_or_none() is None:
            raise PublicationVersionConflictError("Публикация уже изменена.")
