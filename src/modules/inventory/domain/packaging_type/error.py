from src.modules.inventory.domain.error import InventoryError


class InvalidPackagingTypeError(InventoryError):
    """Сообщает о некорректной конфигурации типа тары."""
