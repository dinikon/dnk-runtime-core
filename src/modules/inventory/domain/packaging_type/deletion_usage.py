from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackagingTypeDeletionUsage:
    """Передаёт доменной проверке наличие хотя бы одной сохранённой упаковки товара."""

    has_item_packagings: bool
