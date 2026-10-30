from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.domain.product_representation.value_object import (
    CatalogContentSnapshot,
    RepresentationPreparation,
)


@dataclass(frozen=True, slots=True)
class RepresentationBindingItem:
    """Стабильная пара группы для подготовки и будущих overrides."""

    id: UUID
    catalog_position_id: UUID
    publication_id: UUID


@dataclass(frozen=True, slots=True)
class RepresentationBindingSource:
    """Локальная проекция якорей группы и её пар без восстановления агрегата."""

    id: UUID
    connection_id: UUID
    catalog_root_id: UUID
    mode: BindingMode
    publication_root_id: UUID | None
    revision: int
    items: tuple[RepresentationBindingItem, ...]


@dataclass(frozen=True, slots=True)
class RepresentationCatalogFamily:
    """Согласованный многоязычный снимок семьи из публичного контракта Catalog."""

    root: CatalogContentSnapshot
    positions: tuple[CatalogContentSnapshot, ...]


@dataclass(frozen=True, slots=True)
class PreparedRepresentation:
    """Вычисленное представление для preview и будущих API/XML потребителей."""

    channel_id: UUID
    connection_id: UUID
    binding_group_id: UUID
    binding_revision: int
    config_revision: int
    platform: str
    mode: BindingMode
    locales: tuple[str, ...]
    as_of: datetime
    preparation: RepresentationPreparation
