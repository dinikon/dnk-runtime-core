from src.modules.inventory.domain.error import InventoryError


class ShipmentError(InventoryError):
    """Базовая ошибка плана собственной отгрузки."""


class InvalidShipmentAssignmentSnapshotError(ShipmentError):
    """Отклоняет некорректный снимок назначения или отмены производного черновика."""


class InvalidShipmentFulfillmentSnapshotError(ShipmentError):
    """Отклоняет некорректный полный снимок фактического прогресса для FulfillmentPlan."""


class InvalidShipmentFulfillmentSourceError(ShipmentError):
    """Требует типизированное основание плана и строгую неотрицательную версию."""


class InvalidFulfillmentShipmentLineBindingError(ShipmentError):
    """Отклоняет некорректное назначение распределения новой строке отгрузки."""


class ShipmentFulfillmentMismatchError(ShipmentError):
    """Отклоняет несовпадение отгрузки с распределениями или полными удержаниями плана."""


class StaleShipmentFulfillmentSourceError(ShipmentError):
    """Требует прежнюю версию того же плана без скрытого обновления основания."""


class ShipmentFulfillmentSourceRequiredError(ShipmentError):
    """Запрещает обычное подтверждение без повторной проверки основания FulfillmentPlan."""


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
    """Запрещает операцию в неподходящем состоянии жизненного цикла отгрузки."""


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


class InvalidShipmentExecutionBindingError(ShipmentError):
    """Сообщает о нетипизированном соответствии фактической и плановой строки отгрузки."""


class InvalidShipmentExecutionPlanSnapshotError(ShipmentError):
    """Сообщает о некорректном снимке текущего плана и прогресса отгрузки."""


class InvalidShipmentExecutionRegistrationSnapshotError(ShipmentError):
    """Сообщает о некорректном результате назначения фактических строк отгрузке."""


class ShipmentExecutionMismatchError(ShipmentError):
    """Отклоняет несовместимые исполнение, область или привязки к строкам и резервам."""


class ShipmentQuantityExceededError(ShipmentError):
    """Запрещает накопленную отгрузку сверх планового количества строки."""


class InvalidShipmentDocumentSnapshotError(ShipmentError):
    """Сообщает о некорректном специализированном снимке остатков для расходного документа."""
