"""Неизменяемые снимки контента и результат его подготовки без хранения и I/O."""

from dataclasses import dataclass
from enum import StrEnum

from src.modules.channels.domain.catalog_binding.value_object import (
    BindingAssessment,
    PublicationNode,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentOrigin(StrEnum):
    """Различает собственное значение Catalog, наследование и отсутствие поля."""

    CATALOG = "catalog"
    CATALOG_PARENT = "catalog_parent"
    MISSING = "missing"
    GROUP_OVERRIDE = "group_override"
    ITEM_OVERRIDE = "item_override"


@dataclass(frozen=True, slots=True)
class FieldOrigin:
    """Указывает владельца эффективного значения выбранной локали."""

    kind: ContentOrigin
    catalog_position_id: EntityIdVO | None


@dataclass(frozen=True, slots=True)
class ContentOrigins:
    """Хранит происхождение каждого независимо наследуемого поля."""

    title: FieldOrigin
    body: FieldOrigin
    gallery: FieldOrigin


@dataclass(frozen=True, slots=True)
class ContentImage:
    """Ссылается на Files без авторизованных Console URL и данных хранения."""

    file_id: EntityIdVO
    alt: str
    caption: str


@dataclass(frozen=True, slots=True)
class LocalizedContent:
    """Сохраняет различие отсутствующего поля, пустого описания и пустой галереи.

    Изображения упорядочены; первое изображение является главным.
    """

    locale: str
    title: str | None
    body: str | None
    gallery: tuple[ContentImage, ...] | None
    origins: ContentOrigins


@dataclass(frozen=True, slots=True)
class CatalogContentSnapshot:
    """Передаёт эффективный контент одной позиции для всех запрошенных локалей."""

    id: EntityIdVO
    kind: str
    content: tuple[LocalizedContent, ...]


@dataclass(frozen=True, slots=True)
class PublicationContentSnapshot:
    """Передаёт внешнюю цель без raw, credentials и платформенной модели."""

    structure: PublicationNode
    external_id: str | None
    stale: bool


@dataclass(frozen=True, slots=True)
class RepresentationIssue:
    """Безопасная причина блокировки группы или конкретного поля цели."""

    code: str
    publication_id: EntityIdVO | None = None
    field: str | None = None
    locale: str | None = None


class ContentTargetRole(StrEnum):
    """Отделяет общий контейнер от сопоставленной продаваемой позиции."""

    CONTAINER = "container"
    POSITION = "position"


@dataclass(frozen=True, slots=True)
class PreparedPublicationContent:
    """Контент существующей внешней цели; готовность не означает разрешение экспорта."""

    publication_id: EntityIdVO
    external_id: str | None
    parent_publication_id: EntityIdVO | None
    publication_kind: str | None
    binding_item_id: EntityIdVO | None
    catalog_position_id: EntityIdVO
    role: ContentTargetRole
    content: tuple[LocalizedContent, ...]
    issues: tuple[RepresentationIssue, ...]
    catalog_content: tuple[LocalizedContent, ...] = ()

    @property
    def ready(self) -> bool:
        """Проверяет только полноту локальной подготовки контента этой цели."""
        return not self.issues


@dataclass(frozen=True, slots=True)
class RepresentationPreparation:
    """Результат чистой политики без ревизий хранения и транспортных моделей."""

    assessment: BindingAssessment
    targets: tuple[PreparedPublicationContent, ...]
    issues: tuple[RepresentationIssue, ...]
