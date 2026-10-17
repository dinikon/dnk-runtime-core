from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import dataclass

DEFAULT_TYPE_ID = EntityIdVO.from_value("c0000000-0000-4000-8000-000000000001")
BLOCK_IDS = {
    code: EntityIdVO.from_value(f"c0000000-0000-4000-8000-{i+2:012d}")
    for i, code in enumerate(("name", "desc", "short_desc"))
}


@dataclass(frozen=True, slots=True)
class ContentBlockSnapshot:
    """Неизменяемое определение разрешённого контентного блока."""

    id: EntityIdVO
    code: str
    value_type: str
    required: bool
    position: int
    label: str | None = None


@dataclass(frozen=True, slots=True)
class ProductTypeSchemaSnapshot:
    """Системная схема Default без редактора типов в MVP."""

    id: EntityIdVO
    code: str
    schema_version: int
    blocks: tuple[ContentBlockSnapshot, ...]
    label: str | None = None
