from dataclasses import dataclass

from src.modules.inventory.application.sku.query.get_sku.dto import SkuDetailsDTO


@dataclass(frozen=True, slots=True)
class ListSkusResultDTO:
    """Страница учётных позиций."""

    skus: tuple[SkuDetailsDTO, ...]
