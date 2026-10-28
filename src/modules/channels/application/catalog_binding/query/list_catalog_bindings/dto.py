from dataclasses import dataclass
from src.modules.channels.application.catalog_binding.contracts import BindingGroupDTO


@dataclass(frozen=True, slots=True)
class ListCatalogBindingsResultDTO:
    """Результат сценария list_catalog_bindings."""

    items: tuple[BindingGroupDTO, ...]
    total: int
    offset: int
    limit: int
