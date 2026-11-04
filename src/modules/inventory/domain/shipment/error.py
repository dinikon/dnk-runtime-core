from src.modules.inventory.domain.error import InventoryError


class ShipmentError(InventoryError):
    """Базовая ошибка плана собственной отгрузки."""


class InvalidShipmentValueError(ShipmentError):
    """Сообщает о некорректных собственных значениях или версии плана."""


class InvalidShipmentOrderRefError(ShipmentError):
    """Сообщает о некорректной внешней ссылке заказа."""


class InvalidShipmentLineError(ShipmentError):
    """Сообщает о некорректном собственном составе строки отгрузки."""


class InvalidShipmentOrderSnapshotError(ShipmentError):
    """Сообщает о некорректном снимке заказа и его оставшихся количеств."""


class InvalidShipmentContextError(ShipmentError):
    """Сообщает о несовпадении основания или составе переданных снимков."""


class ShipmentStatusError(ShipmentError):
    """Запрещает изменение плана вне черновика."""


class ShipmentVersionConflictError(ShipmentError):
    """Отклоняет изменение по версии, отличной от текущей версии плана."""


class ShipmentTimeError(ShipmentError):
    """Требует aware-время, UTC-хранение и неубывающую хронологию плана."""


class ShipmentLineConflictError(ShipmentError):
    """Запрещает повтор идентификатора строки или резерва внутри одной отгрузки."""


class ShipmentLineNotFoundError(ShipmentError):
    """Сообщает об отсутствии запрошенной строки в данном плане."""


class ShipmentReservationMismatchError(ShipmentError):
    """Сообщает о несовпадении резерва, основания, товара или области отгрузки."""


class ShipmentItemMismatchError(ShipmentError):
    """Сообщает о другом товаре в текущем снимке строки."""


class ShipmentUomMismatchError(ShipmentError):
    """Запрещает переинтерпретацию плана в другой базовой единице."""


class ShipmentReservationUnavailableError(ShipmentError):
    """Запрещает планировать отгрузку по закрытому, пустому или истёкшему резерву."""


class ShipmentReservationQuantityExceededError(ShipmentError):
    """Запрещает план сверх текущего удерживаемого количества резерва."""


class ShipmentOrderQuantityExceededError(ShipmentError):
    """Запрещает сумме строк отгрузки превышать оставшееся количество строки заказа."""


class ShipmentOrderUnavailableError(ShipmentError):
    """Запрещает подтверждение по заказу, недоступному для исполнения."""


class EmptyShipmentError(ShipmentError):
    """Запрещает подтверждение пустого плана отгрузки."""
