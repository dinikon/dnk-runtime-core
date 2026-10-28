from dataclasses import dataclass
from src.modules.channels.application.catalog_binding.contracts import BindingGroupDTO


@dataclass(frozen=True, slots=True)
class GetCatalogBindingResultDTO:
    """Результат сценария get_catalog_binding."""

    binding: BindingGroupDTO
