from src.modules.inventory.domain.error import InventoryError


class ValuationPostingError(InventoryError):
    """Базовая ошибка регистрации стоимости физического проведения."""


class InvalidValuationPostingValueError(ValuationPostingError):
    """Отклоняет некорректный собственный состав стоимостного проведения."""


class InvalidValuationEntryError(ValuationPostingError):
    """Отклоняет некорректные ссылки, количество, стоимость или направления дельт записи."""


class InvalidValuationEntryBindingError(ValuationPostingError):
    """Требует номинальные идентификаторы слоя и будущей записи стоимости."""


class ValuationPostingSourceError(ValuationPostingError):
    """Отклоняет неподходящее, неполное или несовпадающее основание регистрации стоимости."""


class DuplicateValuationEntryError(ValuationPostingError):
    """Запрещает повторение записей, слоёв и привязок в одном проведении."""


class ValuationPostingTimeError(ValuationPostingError):
    """Требует явные aware-даты и регистрацию стоимости не раньше её оснований."""
