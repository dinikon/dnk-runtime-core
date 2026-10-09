from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetContentBlockDetailsDTO:
    """Результат конкретного сценария get_content_block."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    value_type: str
