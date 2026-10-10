from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AttributeOptionDetailsDTO:
    """Option в результате get_attribute, с подписью выбранной locale."""

    id: UUID
    code: str
    label: str | None
    position: int
    locales: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GetAttributeDetailsDTO:
    """Полный read-контракт сценария get_attribute."""

    id: UUID
    code: str
    value_type: str
    label: str | None
    revision: int
    locales: tuple[str, ...]
    options: tuple[AttributeOptionDetailsDTO, ...]
