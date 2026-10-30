from dataclasses import dataclass
from src.modules.channels.application.content_media.contracts import PreparedGallery


@dataclass(frozen=True, slots=True)
class PrepareGalleryResultDTO:
    """Результат prepare_gallery без документов хранения."""

    galleries: tuple[PreparedGallery, ...]
