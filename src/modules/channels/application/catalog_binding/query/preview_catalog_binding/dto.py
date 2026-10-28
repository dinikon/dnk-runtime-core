from dataclasses import dataclass
from src.modules.channels.application.catalog_binding.contracts import BindingPreviewDTO


@dataclass(frozen=True, slots=True)
class PreviewCatalogBindingResultDTO:
    """Результат сценария preview_catalog_binding."""

    preview: BindingPreviewDTO
