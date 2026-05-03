from dataclasses import dataclass, field

from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind


@dataclass(frozen=True, slots=True)
class FieldSeed:
    """Raw seed-описание поля runtime-объекта до нормализации."""

    name: str
    type: str
    label: str
    description: str = ""
    is_nullable: bool = True
    default: str | None = None
    kind: FieldKind | str = FieldKind.STANDARD
    options: dict[str, str] = field(default_factory=dict)
    settings: dict[str, str] = field(default_factory=dict)
