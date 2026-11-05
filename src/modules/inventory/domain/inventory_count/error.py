from src.modules.inventory.domain.error import InventoryError


class InventoryCountError(InventoryError):
    """Базовая ошибка плана инвентаризации."""


class InvalidInventoryCountValueError(InventoryCountError):
    """Сообщает о некорректном собственном составе или версии плана."""


class InvalidCountScopeError(InventoryCountError):
    """Отклоняет неверный тип проверки, состав или повтор локаций."""


class InventoryCountContextMismatchError(InventoryCountError):
    """Отклоняет чужой склад или неполный, лишний либо повторный набор локаций."""


class InventoryCountStatusError(InventoryCountError):
    """Запрещает изменение плана после выхода из черновика."""


class InventoryCountVersionConflictError(InventoryCountError):
    """Сообщает об устаревшей ожидаемой версии инвентаризации."""


class InventoryCountTimeError(InvalidInventoryCountValueError):
    """Требует явный часовой пояс и неубывающую UTC-хронологию."""


class InvalidInventoryCountBaselineError(InventoryCountError):
    """Отклоняет некорректный состав или ссылку на учётное основание."""


class InvalidInventoryCountStartPlanError(InventoryCountError):
    """Отклоняет неверный снимок текущего плана запуска."""


class InventoryCountBaselineChangedError(InventoryCountError):
    """Требует повторного пересчёта после изменения позиций или состава адресов основания."""


class InvalidInventoryCountSheetSourceError(InventoryCountError):
    """Отклоняет неверный снимок состояния инвентаризации для ведомостей пересчёта."""
