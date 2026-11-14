from src.modules.inventory.domain.inventory_item.error import (
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class InventoryTrackingPolicy:
    """Согласует идентификацию товара и контроль срока из единственного источника — партии."""

    @staticmethod
    def ensure_compatible(
        *, tracking_mode: TrackingMode, expiration_mode: ExpirationMode
    ) -> None:
        """Требует партийный учёт для обязательного срока, не меняя настройки автоматически."""
        if not isinstance(tracking_mode, TrackingMode) or not isinstance(
            expiration_mode, ExpirationMode
        ):
            raise InvalidTrackingConfigurationError(
                "Нужны типизированные режимы прослеживаемости и срока."
            )
        if expiration_mode.controls_expiration and tracking_mode not in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            raise InvalidTrackingConfigurationError(
                "Обязательный срок годности требует учёта по партиям: LOT или LOT_AND_SERIAL."
            )
