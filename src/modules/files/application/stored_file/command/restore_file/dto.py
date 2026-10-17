from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RestoreFileResultDTO:
    """Подтверждение доступности восстановленного файла."""

    file_id: UUID
    status: str
