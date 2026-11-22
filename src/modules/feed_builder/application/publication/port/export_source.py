from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)

type CatalogReference = tuple[UUID, UUID | None]
type PublicationCursor = tuple[datetime, UUID]


@dataclass(frozen=True, slots=True)
class PublicationExportSource:
    """Передаёт привязку и ручные значения без восстановления агрегата."""

    id: UUID
    reference: CatalogReference
    overrides: tuple[FieldOverrideVO, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PublicationEditorSource:
    """Передаёт привязку, ручные значения и версию одной карточки."""

    publication: PublicationExportSource
    version: int
    archived: bool


class PublicationExportReaderProtocol(Protocol):
    """Читает стабильные пакеты включённых публикаций."""

    async def read_for_editor(
        self, feed_id: FeedIdVO, publication_id: UUID
    ) -> PublicationEditorSource | None:
        """Читает одну публикацию независимо от её участия в экспорте."""
        ...

    async def count_enabled(self, feed_id: FeedIdVO) -> int:
        """Считает включённые публикации фида."""
        ...

    async def read_enabled(
        self,
        feed_id: FeedIdVO,
        limit: int,
        before: PublicationCursor | None = None,
    ) -> tuple[PublicationExportSource, ...]:
        """Возвращает публикации от новых к старым с курсором по дате и ID."""
        ...


class PublicationCatalogValuesPort(Protocol):
    """Читает подготовленные Catalog значения для пакета продаваемых позиций."""

    async def read(
        self,
        references: tuple[CatalogReference, ...],
        as_of: datetime,
        locales: frozenset[str],
        sources: frozenset[str],
    ) -> dict[CatalogReference, PublicationCatalogSnapshotVO]:
        """Сохраняет привязку по паре ID и опускает недоступные позиции."""
        ...


class PublicationCatalogAccessPort(Protocol):
    """Проверяет права на запрошенные позиции до получения значений."""

    async def ensure_readable(self, identifiers: tuple[UUID, ...]) -> None:
        """Отклоняет пакет, если недоступен хотя бы один ресурс."""
        ...
