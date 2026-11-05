from src.modules.inventory.domain.error import InventoryError


class CountSheetError(InventoryError):
    """Базовая ошибка ведомости пересчёта."""


class InvalidCountSheetValueError(CountSheetError):
    """Отклоняет неверный собственный состав ведомости или строгую версию."""


class InvalidCountLineError(CountSheetError):
    """Отклоняет неверный состав строки или количество конкретного SERIAL."""


class InvalidCountSheetLineBindingError(CountSheetError):
    """Требует типизированное назначение ID строки позиции учётного основания."""


class CountSheetSourceMismatchError(CountSheetError):
    """Отклоняет чужую инвентаризацию, основание, товар, единицу или состав исходных позиций."""


class CountSheetLineConflictError(CountSheetError):
    """Запрещает повтор ID строки, позиции или измерений в ведомости."""


class CountSheetLineNotFoundError(CountSheetError):
    """Сообщает об отсутствии строки в данной ведомости."""


class CountSheetStatusError(CountSheetError):
    """Запрещает изменение результатов после передачи или отмены ведомости."""


class CountSheetVersionConflictError(CountSheetError):
    """Отклоняет переход по устаревшей ожидаемой версии ведомости."""


class CountSheetTimeError(InvalidCountSheetValueError):
    """Требует явные UTC-моменты и согласованную хронологию ввода и пересчёта."""


class UncountedCountSheetError(CountSheetError):
    """Запрещает передачу ведомости с непосчитанными строками."""
