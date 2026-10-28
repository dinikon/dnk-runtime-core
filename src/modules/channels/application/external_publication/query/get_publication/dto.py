"""Результат конкретного сценария публикаций."""

from dataclasses import dataclass

from src.modules.channels.application.external_publication.representation import (
    PublicationCardView,
)


@dataclass(frozen=True, slots=True)
class GetPublicationResultDTO:
    """Передаёт проекции и доступные языки без нативных документов."""

    card: PublicationCardView
    locale: str
    locales: tuple[str, ...]
