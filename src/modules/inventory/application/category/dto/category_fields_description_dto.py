from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CategoryFieldOptionDTO:
    """DTO одной select-option в описании поля категории."""

    value: str
    label: str


@dataclass(frozen=True, slots=True)
class CategoryFieldDescriptionDTO:
    """DTO описания поля категории."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: tuple[CategoryFieldOptionDTO, ...]
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class CategoryObjectDescriptionDTO:
    """DTO описания runtime-объекта product_category."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class CategoryFieldsDescriptionDTO:
    """DTO описания модели категории товаров и ее полей."""

    object_description: CategoryObjectDescriptionDTO
    fields: tuple[CategoryFieldDescriptionDTO, ...]
