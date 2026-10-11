from dataclasses import dataclass
from uuid import UUID

from src.modules.files.application.port.storage import FileContentStream


@dataclass(frozen=True, slots=True)
class GetFilePreviewResultDTO:
    """Передаёт поток и метаданные отдельного сценария предпросмотра файла."""

    file_id: UUID
    name: str
    content_type: str
    size_bytes: int
    stream: FileContentStream
