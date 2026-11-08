from src.modules.inventory.domain.error import InventoryError


class FulfillmentPlanError(InventoryError):
    """Базовая ошибка ручного планирования исполнения заказа."""


class FulfillmentSupplierOrderAssignmentError(FulfillmentPlanError):
    """Отклоняет неполное, изменённое или конфликтующее назначение внешнего заказа."""


class FulfillmentReplanningConflictError(FulfillmentPlanError):
    """Запрещает замену неподходящих распределений или нарушение истории и действующих обязательств."""


class FulfillmentAllocationCancellationConflictError(FulfillmentPlanError):
    """Запрещает отмену неподходящего распределения или некорректный пакет выбора строк."""


class FulfillmentAllocationExtensionConflictError(FulfillmentPlanError):
    """Отклоняет несвежие распределения, повтор ID или некорректный пакет допланирования."""


class InvalidFulfillmentReservationReleaseRefError(FulfillmentPlanError):
    """Отклоняет некорректную историю снятого резервного подтверждения."""


class FulfillmentReservationReleaseConflictError(FulfillmentPlanError):
    """Запрещает снятие неподходящего подтверждения, назначенного или исполненного распределения."""


class InvalidFulfillmentShipmentAssignmentError(FulfillmentPlanError):
    """Отклоняет некорректную ссылку назначения Shipment."""


class FulfillmentShipmentAssignmentConflictError(FulfillmentPlanError):
    """Запрещает конкурирующее назначение, несовместимое снятие или изменение назначенного отправления."""


class InvalidFulfillmentShipmentProgressRefError(FulfillmentPlanError):
    """Отклоняет некорректную контрольную точку прогресса строки Shipment."""


class FulfillmentShipmentProgressMismatchError(FulfillmentPlanError):
    """Отклоняет чужую отгрузку, состав распределений или изменение прежней привязки."""


class FulfillmentShipmentProgressConflictError(FulfillmentPlanError):
    """Отклоняет уменьшение количества, устаревший снимок или разные данные одной версии."""


class InvalidFulfillmentPlanShipmentSnapshotError(FulfillmentPlanError):
    """Отклоняет некорректное основание отгрузки из полностью подтверждённого плана."""


class InvalidFulfillmentReservationRefError(FulfillmentPlanError):
    """Отклоняет некорректную историческую ссылку на подтверждённый резерв."""


class InvalidFulfillmentReservationBindingError(FulfillmentPlanError):
    """Отклоняет нетипизированное назначение распределения резерву или неверную версию."""


class FulfillmentReservationMismatchError(FulfillmentPlanError):
    """Отклоняет резерв другой строки, области, единицы или количества."""


class FulfillmentReservationUnavailableError(FulfillmentPlanError):
    """Запрещает подтверждение неполным, погашенным, закрытым или истёкшим удержанием."""


class FulfillmentReservationVersionConflictError(FulfillmentPlanError):
    """Отклоняет изменившуюся версию нового либо ранее закреплённого резерва."""


class FulfillmentReservationConflictError(FulfillmentPlanError):
    """Запрещает повторное подтверждение распределения или повторное использование резерва."""


class InvalidFulfillmentPlanValueError(FulfillmentPlanError):
    """Отклоняет некорректный собственный состав или версию плана."""


class InvalidFulfillmentAllocationError(FulfillmentPlanError):
    """Отклоняет некорректные ссылки, единицу или неположительное количество распределения."""


class InvalidFulfillmentOrderRefError(FulfillmentPlanError):
    """Отклоняет пустую или нетипизированную внешнюю ссылку заказа."""


class InvalidFulfillmentSourceError(FulfillmentPlanError):
    """Отклоняет неподдержанный вид или нетипизированный склад источника."""


class InvalidFulfillmentDemandError(FulfillmentPlanError):
    """Отклоняет некорректный снимок потребности или повторные ссылки строк заказа."""


class FulfillmentPlanContextError(FulfillmentPlanError):
    """Отклоняет чужой заказ, товар, единицу, склад или неверный состав текущих снимков."""


class FulfillmentSupplierOrderConfirmationError(FulfillmentPlanError):
    """Отклоняет подтверждение, не соответствующее закреплённому внешнему заказу."""


class FulfillmentSupplierOrderRejectionError(FulfillmentPlanError):
    """Отклоняет отказ, не соответствующий закреплённому внешнему заказу."""


class FulfillmentSupplierOrderShipmentError(FulfillmentPlanError):
    """Отклоняет внешнюю отправку, не соответствующую подтверждённому обязательству."""


class FulfillmentPlanStatusError(FulfillmentPlanError):
    """Запрещает операцию в неподходящем состоянии плана."""


class FulfillmentPlanVersionConflictError(FulfillmentPlanError):
    """Отклоняет изменение по устаревшей ожидаемой версии."""


class FulfillmentPlanTimeError(InvalidFulfillmentPlanValueError):
    """Требует явное время с часовым поясом, хранение в UTC и неубывающую хронологию."""


class FulfillmentAllocationConflictError(FulfillmentPlanError):
    """Запрещает повтор ID, пары строка/источник или разную идентичность одной строки заказа."""


class FulfillmentAllocationNotFoundError(FulfillmentPlanError):
    """Сообщает об отсутствии распределения в данном плане."""


class FulfillmentDemandExceededError(FulfillmentPlanError):
    """Запрещает сумме распределений превышать текущую потребность строки заказа."""


class FulfillmentSourceSplitForbiddenError(FulfillmentPlanError):
    """Запрещает несколько источников для строки заказа, не разрешающей разделение."""


class FulfillmentOrderUnavailableError(FulfillmentPlanError):
    """Запрещает планирование по заказу, недоступному для исполнения."""


class EmptyFulfillmentPlanError(FulfillmentPlanError):
    """Запрещает фиксацию пустого плана исполнения."""
