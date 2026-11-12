from pydantic import RootModel

from src.modules.catalog.presentation.catalog_item.http.inventory_item_selection_value import (
    InventoryItemSelectionValue,
)


class SetCatalogItemSkuRequest(RootModel[InventoryItemSelectionValue]):
    """Принимает один из трёх явных вариантов назначения SKU корню."""
