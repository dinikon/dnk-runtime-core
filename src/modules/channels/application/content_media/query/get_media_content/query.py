from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetMediaContentQuery:
    """Параметры ограниченного внешнего чтения без Console principal."""

    media_id: UUID
    token: str = field(repr=False)
    metadata_only: bool = False
    extension: str | None = None
