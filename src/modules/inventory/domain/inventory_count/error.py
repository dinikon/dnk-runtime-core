from src.modules.inventory.domain.error import InventoryError


class InventoryCountError(InventoryError):
    """Базовая ошибка плана инвентаризации."""


class InventoryCountCompletionError(InventoryCountError):
    """Отклоняет несогласованные сведения или факты завершения инвентаризации."""


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


class InvalidInventoryCountResultError(InventoryCountError):
    """Отклоняет некорректное значение или собственный состав сводного результата."""


class InventoryCountResultMismatchError(InventoryCountError):
    """Отклоняет результат, не соответствующий текущим источникам инвентаризации."""


class InventoryCountCoverageError(InventoryCountError):
    """Требует точное полное покрытие всех позиций учётного основания."""


class InventoryCountResultConflictError(InventoryCountError):
    """Запрещает повтор ведомости, позиции или найденных измерений в сводном результате."""


class InventoryCountSerialConflictError(InventoryCountResultConflictError):
    """Отклоняет несовместимую идентичность или несколько положительных наблюдений одного SERIAL в области."""


class InventoryCountSheetsNotReadyError(InventoryCountError):
    """Запрещает фиксацию сводного результата при наличии незавершённых черновиков."""
