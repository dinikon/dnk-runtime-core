from src.modules.channels.domain.stock_sync.state import DesiredStockVO

"""Конкретные read-проекции и снимки границ привязки."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingMode,
    BindingAssessment,
)


@dataclass(frozen=True, slots=True)
class BindingPairDTO:
    """Пара UUID без данных Catalog или площадки."""

    catalog_position_id: UUID
    publication_id: UUID


@dataclass(frozen=True, slots=True)
class BindingPositionDTO:
    """Публичные поля сравнения; денежные значения остаются строками."""

    id: UUID
    kind: str
    title: str | None
    sku: str | None
    image_url: str | None
    status: str | None
    price: str | None
    currency: str | None
    quantity: str | None
    availability: str | None
    stock_source_id: UUID
    external_id: str | None = None
    stale: bool = False
    backorders: str = "no"
    stock: DesiredStockVO | None = None


@dataclass(frozen=True, slots=True)
class CatalogStructureDTO:
    """UUID-представление структуры в публичной read-проекции."""

    id: UUID
    kind: str
    positions: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class PublicationStructureDTO:
    """UUID-представление топологии публикации."""

    id: UUID
    kind: str
    parent_id: UUID | None


@dataclass(frozen=True, slots=True)
class CatalogFamilyDTO:
    """Семья Catalog с отделёнными структурой и отображением."""

    structure: CatalogStructureDTO
    root: BindingPositionDTO
    positions: tuple[BindingPositionDTO, ...]


@dataclass(frozen=True, slots=True)
class PublicationNodeDTO:
    """Нормализованное представление публикации без raw/platform документов."""

    structure: PublicationStructureDTO
    position: BindingPositionDTO


@dataclass(frozen=True, slots=True)
class BindingRecord:
    """SQL read-проекция группы без Aggregate restore."""

    id: UUID
    connection_id: UUID
    channel_id: UUID
    channel_name: str
    platform: str
    catalog_root_id: UUID
    mode: BindingMode
    publication_root_id: UUID | None
    revision: int
    items: tuple[BindingPairDTO, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class BindingPreviewDTO:
    """Актуальный контекст формы и структурные токены."""

    catalog: CatalogFamilyDTO | None
    publications: tuple[BindingPositionDTO, ...]
    assessment: BindingAssessment
    catalog_token: str
    publication_token: str
    suggestions: tuple[BindingPairDTO, ...]


@dataclass(frozen=True, slots=True)
class BindingGroupDTO:
    """Полный публичный результат группы с вычисляемым состоянием."""

    group: BindingRecord
    preview: BindingPreviewDTO


@dataclass(frozen=True, slots=True)
class BindingCandidatesDTO:
    """Страница кандидатов с закреплениями текущего подключения."""

    items: tuple[BindingPositionDTO, ...]
    occupied_ids: tuple[UUID, ...]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class BindingConnectionDTO:
    """Минимальный контекст подключения для локальных read-сценариев."""

    id: UUID
    platform: str
