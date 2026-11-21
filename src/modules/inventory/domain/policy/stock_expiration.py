from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.error import (
    ExpirationDateNotAllowedError,
    ExpirationDateRequiredError,
    InvalidStockDatesError,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


class StockExpirationPolicy:
    """Разделяет допустимость заполнения дат и обязательность срока перед поступлением."""

    @staticmethod
    def ensure_dates_allowed(
        *, dates: StockDatesVO, expiration_mode: ExpirationMode
    ) -> None:
        """Разрешает неполную карточку, запрещая срок годности только в режиме NONE."""
        if not isinstance(dates, StockDatesVO):
            raise InvalidStockDatesError("Ожидалось значение StockDatesVO.")
        if not isinstance(expiration_mode, ExpirationMode):
            raise InvalidTrackingConfigurationError("Ожидался режим ExpirationMode.")
        if expiration_mode is ExpirationMode.NONE and dates.expires_on is not None:
            raise ExpirationDateNotAllowedError(
                "В режиме NONE срок годности не заполняется."
            )

    @staticmethod
    def ensure_ready_for_receipt(
        *, dates: StockDatesVO, expiration_mode: ExpirationMode
    ) -> None:
        """Требует дату для REQUIRED, не определяя допустимость приёмки просрочки."""
        StockExpirationPolicy.ensure_dates_allowed(
            dates=dates, expiration_mode=expiration_mode
        )
        if expiration_mode.controls_expiration and dates.expires_on is None:
            raise ExpirationDateRequiredError(
                "Перед поступлением в режиме REQUIRED укажите срок годности."
            )

    @staticmethod
    def ensure_operation_allowed(
        *,
        dates: StockDatesVO | None,
        expiration_mode: ExpirationMode,
        operation_type: StockOperationType,
    ) -> None:
        """Проверяет заполнение срока поступления, не запрещая учёт просрочки в других операциях."""
        if not isinstance(expiration_mode, ExpirationMode) or not isinstance(
            operation_type, StockOperationType
        ):
            raise InvalidTrackingConfigurationError(
                "Нужны типизированные режим срока и вид операции."
            )
        if dates is not None:
            StockExpirationPolicy.ensure_dates_allowed(
                dates=dates, expiration_mode=expiration_mode
            )
        if (
            operation_type is StockOperationType.RECEIPT
            and expiration_mode.controls_expiration
        ):
            if dates is None:
                raise ExpirationDateRequiredError(
                    "Перед поступлением нужен срок годности партии."
                )
            StockExpirationPolicy.ensure_ready_for_receipt(
                dates=dates, expiration_mode=expiration_mode
            )
