from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from src.modules.channels.domain.error import ChannelsValidationError

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[
    str, JsonValue
]


@dataclass(frozen=True, slots=True)
class PublicationCoreVO:
    """Хранит нормализованные наблюдаемые значения, не канонический товар."""

    resource_type: str
    external_id: str
    external_sku: str | None
    price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    stock_status: str
    title: str | None
    title_locale: str | None
    main_image_url: str | None
    source_updated_at: datetime | None
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        """Проверяет базовую identity и безопасные нормализованные типы."""
        if (
            not self.external_id
            or len(self.external_id) > 200
            or (not self.resource_type)
            or (len(self.resource_type) > 80)
        ):
            raise ChannelsValidationError("invalid_publication_identity")
        validate_observed_values(
            self.price, self.sale_price, self.quantity, self.stock_status
        )
        if (
            self.source_updated_at is not None
            and self.source_updated_at.utcoffset() is None
        ):
            raise ChannelsValidationError("invalid_source_timezone")


def validate_observed_values(
    price: Decimal | None,
    sale_price: Decimal | None,
    quantity: Decimal | None,
    stock_status: str,
) -> None:
    """Проверяет общие ограничения наблюдаемых денег и наличия без identity."""
    if stock_status not in (
        "in_stock",
        "out_of_stock",
        "on_backorder",
        "unknown",
    ):
        raise ChannelsValidationError("invalid_stock_status")
    for value in (price, sale_price, quantity):
        if value is not None and (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value.copy_abs() >= Decimal("1e18")
            or (value.as_tuple().exponent < -12)
        ):
            raise ChannelsValidationError("invalid_numeric_core")
