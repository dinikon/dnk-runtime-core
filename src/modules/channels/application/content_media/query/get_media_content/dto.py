from dataclasses import dataclass
from src.modules.files.application.port.storage import FileContentStream


@dataclass(frozen=True, slots=True)
class GetMediaContentResultDTO:
    """Метаданные и поток; HEAD возвращает только метаданные."""

    content_type: str
    size_bytes: int
    stream: FileContentStream | None
