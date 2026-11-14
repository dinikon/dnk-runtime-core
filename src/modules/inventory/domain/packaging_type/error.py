from src.modules.inventory.domain.error import InventoryError


class PackagingTypeError(InventoryError):
    """Базовая предметная ошибка справочника типов тары."""


class InvalidPackagingTypeError(PackagingTypeError):
    """Сообщает о некорректной конфигурации типа тары."""


class PackagingTypeNotFoundError(PackagingTypeError):
    """Сообщает об отсутствии типа тары в текущем tenant."""


class PackagingTypeCodeAlreadyExistsError(PackagingTypeError):
    """Сообщает о занятом точном коде типа тары в текущем tenant."""


class PackagingTypeInUseError(PackagingTypeError):
    """Запрещает удаление типа тары, используемого хотя бы одной упаковкой товара."""
