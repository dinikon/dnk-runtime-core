from dataclasses import dataclass
from uuid import UUID
from src.modules.files.application.port.storage import FileContentStream


@dataclass(frozen=True, slots=True)
class GetFileContentResultDTO:
    """Результат сценария get_file_content; не является доменным агрегатом."""

    file_id: UUID
    name: str
    content_type: str
    size_bytes: int
    stream: FileContentStream
