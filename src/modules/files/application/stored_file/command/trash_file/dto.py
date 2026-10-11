from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TrashFileResultDTO:
    """Подтверждение переноса файла с исходными датой и сроком корзины."""

    file_id: UUID
    deleted_at: datetime
    purge_after: datetime
