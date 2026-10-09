from typing import ClassVar

from src.modules.shared.domain.domain_error import DomainError


class WarehouseError(DomainError):
    """Базовая ошибка бизнес-правил склада."""

    code: ClassVar[str] = "warehouse.error"


class InvalidWarehouseCodeError(WarehouseError):
    """Код склада пуст, слишком длинен или содержит недопустимое значение."""

    code = "warehouse.invalid_code"


class InvalidWarehouseTitleError(WarehouseError):
    """Название склада не соответствует ограничениям."""

    code = "warehouse.invalid_title"


class InvalidWarehouseTypeError(WarehouseError):
    """Строковый код типа склада не соответствует ограничениям."""

    code = "warehouse.invalid_type"


class InvalidWarehouseTimezoneError(WarehouseError):
    """Часовой пояс не задан либо отсутствует среди активных кодов справочника."""

    code = "warehouse.invalid_timezone"


class InvalidWarehouseStateError(WarehouseError):
    """Идентификаторы, статус, ревизия или аудит склада нарушают инварианты."""

    code = "warehouse.invalid_state"


class WarehouseCodeAlreadyExistsError(WarehouseError):
    """Нормализованный код уже занят складом текущего tenant."""

    code = "warehouse.code_already_exists"


class WarehouseNotFoundError(WarehouseError):
    """Запрошенный склад отсутствует в текущем tenant."""

    code = "warehouse.not_found"
