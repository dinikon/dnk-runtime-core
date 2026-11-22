from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AddedPublicationDTO:
    """Сопоставляет нормализованную ссылку с новой или существующей публикацией."""

    id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    status: str
    version: int
    outcome: str


@dataclass(frozen=True, slots=True)
class AddCatalogItemsResultDTO:
    """Возвращает итог атомарного пакета после сохранения в общем UoW."""

    feed_id: UUID
    feed_version: int
    items: tuple[AddedPublicationDTO, ...]
