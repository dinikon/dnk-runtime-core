from dataclasses import dataclass
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
)


@dataclass(frozen=True, slots=True)
class PreviewCatalogDraftResultDTO:
    """Возвращает конкретный результат сценария preview_catalog_draft."""

    observed_revision: int
    values: CatalogDraftValuesDTO
    issues: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]
    main_image_url: str | None
    origins: dict[str, str]
