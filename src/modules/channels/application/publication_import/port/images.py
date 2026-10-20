from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DownloadedPublicationImageDTO:
    """Передаёт ограниченный бинарный результат без внешних headers."""

    data: bytes = field(repr=False)
    content_type: str


class PublicationImageDownloader(Protocol):
    """Получает только выбранное сервером изображение без credentials источника."""

    async def download(self, url: str) -> DownloadedPublicationImageDTO:
        """Загружает ограниченное изображение либо безопасный код отказа."""
        ...
