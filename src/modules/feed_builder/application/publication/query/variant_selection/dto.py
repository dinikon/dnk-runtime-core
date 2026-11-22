from dataclasses import dataclass
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogSubject,
)


@dataclass(frozen=True, slots=True)
class VariantSelectionResultDTO:
    """Передаёт полный ограниченный снимок без молчаливого усечения."""

    items: tuple[PublicationCatalogSubject, ...]
