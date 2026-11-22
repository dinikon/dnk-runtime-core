from uuid import UUID
from sqlalchemy.exc import DBAPIError
from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReference,
)
from src.modules.catalog.application.catalog_item.port.publication_reader import (
    CatalogPublicationReaderProtocol,
    CatalogPublicationSubject,
    CatalogPublicationSelectionError,
    CatalogPublicationFamilyNotFoundError,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogSubject,
    PublicationSourceUnavailableError,
    PublicationSelectionLimitError,
    PublicationSourceNotFoundError,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogPublicationReader:
    """Адаптирует публичный owner-контракт без импорта внутренних объектов Catalog."""

    def __init__(self, reader: CatalogPublicationReaderProtocol) -> None:
        """Принимает публичный порт владельца на общей tenant-сессии."""
        self._reader = reader

    @staticmethod
    def _map(subject: CatalogPublicationSubject) -> PublicationCatalogSubject:
        """Явно переводит идентификаторы и подписи во внутренний контракт."""
        return PublicationCatalogSubject(
            CatalogProductReferenceVO(
                EntityIdVO(subject.reference.item_id),
                (
                    EntityIdVO(subject.reference.variant_id)
                    if subject.reference.variant_id
                    else None
                ),
            ),
            subject.kind,
            subject.sku,
            subject.title,
            subject.parent_title,
            subject.available,
        )

    async def read_many(
        self, references: tuple[CatalogProductReferenceVO, ...], locale: str
    ) -> tuple[PublicationCatalogSubject, ...]:
        """Переводит сбой БД в собственную ошибку зависимости."""
        try:
            rows = await self._reader.read_many(
                tuple(
                    CatalogCalculationReference(
                        r.catalog_item_id.uuid,
                        r.catalog_variant_id.uuid if r.catalog_variant_id else None,
                    )
                    for r in references
                ),
                locale,
            )
        except DBAPIError as exc:
            raise PublicationSourceUnavailableError(
                "Catalog временно недоступен."
            ) from exc
        return tuple(self._map(r) for r in rows)

    async def search_ids(self, search: str, locale: str) -> tuple[UUID, ...]:
        """Делегирует поиск владельцу, не создавая межмодульный SQL JOIN."""
        try:
            return await self._reader.search_ids(search, locale)
        except DBAPIError as exc:
            raise PublicationSourceUnavailableError(
                "Catalog временно недоступен."
            ) from exc

    async def variant_selection(
        self, root_id: UUID, locale: str
    ) -> tuple[PublicationCatalogSubject, ...]:
        """Не обрезает молча большие семейства."""
        try:
            return tuple(
                self._map(r)
                for r in await self._reader.variant_selection(root_id, locale)
            )
        except CatalogPublicationFamilyNotFoundError as exc:
            raise PublicationSourceNotFoundError(str(exc)) from exc
        except CatalogPublicationSelectionError as exc:
            raise PublicationSelectionLimitError(str(exc)) from exc
        except DBAPIError as exc:
            raise PublicationSourceUnavailableError(
                "Catalog временно недоступен."
            ) from exc
