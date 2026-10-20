from dataclasses import dataclass
from src.modules.channels.application.publication_import.port.files import (
    PublicationImportImageStream,
)


@dataclass(frozen=True, slots=True)
class GetPublicationImportImageResultDTO:
    """Возвращает поток разрешённого изображения без внешнего URL."""

    content_type: str
    size_bytes: int
    stream: PublicationImportImageStream
