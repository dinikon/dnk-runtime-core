from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FieldSeed:
    """Raw seed-описание поля runtime-объекта до нормализации."""

    name: str
    type: str
    label: str
    description: str = ""
    is_nullable: bool = True
    default: str | None = None
    options: dict[str, str] = field(default_factory=dict)
    settings: dict[str, str] = field(default_factory=dict)
