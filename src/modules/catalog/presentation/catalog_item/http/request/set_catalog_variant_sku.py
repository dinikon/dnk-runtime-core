from pydantic import RootModel

from src.modules.catalog.presentation.catalog_item.http.inventory_item_selection_value import (
    InventoryItemSelectionValue,
)


class SetCatalogVariantSkuRequest(RootModel[InventoryItemSelectionValue]):
    """Принимает назначение собственного SKU варианту внутри заданного родителя."""
