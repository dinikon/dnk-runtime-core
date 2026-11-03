from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidStockDocumentValueError,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockDocumentProgressPolicy:
    """Согласует состояние документа с накопленными количествами его строк."""

    @staticmethod
    def ensure_valid(
        *,
        status: StockDocumentStatus,
        quantities: tuple[tuple[QuantityVO, QuantityVO], ...],
    ) -> None:
        """Разрешает частичное и полное состояние только при соответствующем исполнении."""
        if not isinstance(status, StockDocumentStatus) or not isinstance(
            quantities, tuple
        ):
            raise InvalidStockDocumentValueError(
                "Нужны статус и tuple плановых/выполненных величин."
            )
        for pair in quantities:
            if (
                not isinstance(pair, tuple)
                or len(pair) != 2
                or not all(isinstance(value, QuantityVO) for value in pair)
                or pair[0].value.is_zero()
                or pair[1].value > pair[0].value
            ):
                raise InvalidStockDocumentValueError(
                    "Накопленное исполнение должно находиться между нулём и положительным планом."
                )
        any_done = any(not executed.value.is_zero() for planned, executed in quantities)
        all_done = bool(quantities) and all(
            planned == executed for planned, executed in quantities
        )
        if (
            status
            in (
                StockDocumentStatus.DRAFT,
                StockDocumentStatus.CONFIRMED,
                StockDocumentStatus.CANCELLED,
            )
            and any_done
        ):
            raise InvalidStockDocumentValueError(
                "Состояние документа не допускает выполненного количества."
            )
        if (
            status
            in (
                StockDocumentStatus.CONFIRMED,
                StockDocumentStatus.PARTIALLY_EXECUTED,
                StockDocumentStatus.COMPLETED,
            )
            and not quantities
        ):
            raise EmptyStockDocumentError(
                "Подтверждённый или исполняемый документ не может быть пустым."
            )
        if status is StockDocumentStatus.PARTIALLY_EXECUTED and (
            not any_done or all_done
        ):
            raise InvalidStockDocumentValueError(
                "Частичный статус требует ненулевого неполного исполнения."
            )
        if status is StockDocumentStatus.COMPLETED and not all_done:
            raise InvalidStockDocumentValueError(
                "Завершённый документ требует полного исполнения каждой строки."
            )
