from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CompanyFieldOptionDTO:
    """DTO опции поля CRM-модели company."""

    value: str
    label: str


@dataclass(slots=True, frozen=True)
class CompanyFieldDescriptionDTO:
    """DTO описания поля CRM-модели company."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: tuple[CompanyFieldOptionDTO, ...]
    kind: str = "standard"


@dataclass(slots=True, frozen=True)
class CompanyObjectDescriptionDTO:
    """DTO описания CRM-объекта company."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str = "standard"


@dataclass(slots=True, frozen=True)
class CompanyFieldsDescriptionDTO:
    """DTO описания CRM-модели company и ее полей."""

    object_description: CompanyObjectDescriptionDTO
    fields: tuple[CompanyFieldDescriptionDTO, ...]
