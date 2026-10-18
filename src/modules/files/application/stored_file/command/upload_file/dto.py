from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UploadFileResultDTO:
    """Результат сценария upload_file; не является доменным агрегатом."""

    file_id: UUID
    name: str
    content_type: str
    size_bytes: int
