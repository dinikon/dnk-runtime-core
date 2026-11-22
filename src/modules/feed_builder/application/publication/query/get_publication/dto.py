from dataclasses import dataclass
from src.modules.feed_builder.application.publication.query.list_publications.dto import (
    PublicationListItemDTO,
)


@dataclass(frozen=True, slots=True)
class GetPublicationResultDTO:
    """Передаёт карточку участия и контекст доступности Feed."""

    publication: PublicationListItemDTO
    feed_version: int
    feed_status: str
