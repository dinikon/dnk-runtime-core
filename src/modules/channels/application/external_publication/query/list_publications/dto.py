"""Результат конкретного сценария публикаций."""

from dataclasses import dataclass

from src.modules.channels.application.external_publication.representation import (
    PublicationCardView,
)


@dataclass(frozen=True, slots=True)
class ListPublicationsResultDTO:
    """Передаёт проекции и доступные языки без нативных документов."""

    items: tuple[PublicationCardView, ...]
    total: int
    offset: int
    limit: int
    locale: str
    locales: tuple[str, ...]
