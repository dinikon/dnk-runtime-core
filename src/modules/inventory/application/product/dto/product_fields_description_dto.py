from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProductFieldOptionDTO:
    """DTO одной select-option в описании поля товара."""

    value: str
    label: str


@dataclass(frozen=True, slots=True)
class ProductFieldDescriptionDTO:
    """DTO описания поля товара."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: tuple[ProductFieldOptionDTO, ...]
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class ProductObjectDescriptionDTO:
    """DTO описания runtime-объекта product."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class ProductFieldsDescriptionDTO:
    """DTO описания модели товара и ее полей."""

    object_description: ProductObjectDescriptionDTO
    fields: tuple[ProductFieldDescriptionDTO, ...]
