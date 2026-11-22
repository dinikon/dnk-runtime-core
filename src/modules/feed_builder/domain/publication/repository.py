from typing import Protocol
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_version import (
    FeedPublicationVersionVO,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)


class FeedPublicationRepositoryProtocol(Protocol):
    """Хранит самостоятельные агрегаты в общем tenant UoW."""

    async def find(
        self, feed_id: FeedIdVO, references: tuple[CatalogProductReferenceVO, ...]
    ) -> tuple[FeedPublication, ...]:
        """Находит уже выбранные позиции, включая архивные."""
        ...

    async def get_for_update(self, identifier: FeedPublicationIdVO) -> FeedPublication:
        """Блокирует запись либо сообщает об отсутствии."""
        ...

    async def add_many(self, publications: tuple[FeedPublication, ...]) -> None:
        """Добавляет запись без commit."""
        ...

    async def save(
        self, publication: FeedPublication, expected_version: FeedPublicationVersionVO
    ) -> None:
        """Условно сохраняет изменившийся агрегат без commit."""
        ...
