from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import dataclass
from enum import StrEnum


class BindingMode(StrEnum):
    """Способ представления одной карточки Catalog."""

    SIMPLE_TO_SIMPLE = "SIMPLE_TO_SIMPLE"
    VARIABLE_TO_VARIABLE = "VARIABLE_TO_VARIABLE"
    VARIABLE_TO_SIMPLE = "VARIABLE_TO_SIMPLE"


@dataclass(frozen=True, slots=True)
class CatalogFamily:
    """Минимальные факты владельца Catalog для проверки структуры."""

    id: EntityIdVO
    kind: str
    positions: tuple[EntityIdVO, ...]


@dataclass(frozen=True, slots=True)
class PublicationNode:
    """Структура публикации без нативного JSON."""

    id: EntityIdVO
    kind: str
    parent_id: EntityIdVO | None


@dataclass(frozen=True, slots=True)
class BindingClaim:
    """Закрепление публикации или целой семьи за группой."""

    group_id: EntityIdVO
    publication_id: EntityIdVO


@dataclass(frozen=True, slots=True)
class BindingAssessment:
    """Состояние по известным локальным позициям, а не готовность к экспорту."""

    state: str
    issues: tuple[str, ...]
    catalog_count: int
    publication_count: int
    matched_count: int
