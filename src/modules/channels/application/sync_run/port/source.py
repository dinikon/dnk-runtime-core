"""Типизированные наблюдения источника без зависимостей от нативных моделей."""

from dataclasses import dataclass
from enum import StrEnum

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationKind,
)


class PublicationReadPhase(StrEnum):
    """Общие этапы обхода: позиции и дети ранее полученных карточек."""

    PRODUCTS = "products"
    CHILDREN = "children"


@dataclass(frozen=True, slots=True)
class PublicationCheckpoint:
    """Отделяет общий проход родителей от непрозрачного курсора платформы."""

    phase: PublicationReadPhase = PublicationReadPhase.PRODUCTS
    cursor: JsonObject | None = None
    after_parent: str | None = None
    current_parent: str | None = None

    def to_document(self) -> JsonObject:
        """Сериализует ограниченное состояние без списка товаров."""
        return {
            "phase": self.phase.value,
            "cursor": self.cursor or {},
            "after_parent": self.after_parent,
            "current_parent": self.current_parent,
        }

    @classmethod
    def from_document(cls, document: JsonObject) -> "PublicationCheckpoint":
        """Разбирает собственный envelope, оставляя native cursor пакету."""
        cursor = document.get("cursor", {})
        after, current = document.get("after_parent"), document.get("current_parent")
        if not isinstance(cursor, dict) or any(
            value is not None and not isinstance(value, str)
            for value in (after, current)
        ):
            raise ValueError("Invalid publication checkpoint")
        return cls(
            PublicationReadPhase(document.get("phase", "products")),
            cursor,
            after,
            current,
        )


@dataclass(frozen=True, slots=True)
class PublicationObservation:
    """Передаёт один полный полученный объект и его поддержанную проекцию."""

    resource_type: str
    external_id: str
    kind: PublicationKind
    parent_external_id: str | None
    parent_resource_type: str | None
    raw_data: JsonObject
    data: PublicationData
    platform_schema: str
    platform_data: JsonObject

    @property
    def key(self) -> tuple[str, str]:
        """Возвращает ключ реальной позиции внутри подключения."""
        return self.resource_type, self.external_id


@dataclass(frozen=True, slots=True)
class PublicationPage:
    """Передаёт страницу и ограниченное состояние продолжения обхода."""

    items: tuple[PublicationObservation, ...]
    dependencies: tuple[PublicationObservation, ...]
    checkpoint: PublicationCheckpoint
    done: bool
    processed_count: int
    skipped_count: int = 0
