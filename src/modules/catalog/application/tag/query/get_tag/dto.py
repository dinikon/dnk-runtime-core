from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetTagDetailsDTO:
    """Карточка справочника в сценарии get_tag, без locale fallback."""

    id: UUID
    label: str | None
    revision: int
    locales: tuple[str, ...]
