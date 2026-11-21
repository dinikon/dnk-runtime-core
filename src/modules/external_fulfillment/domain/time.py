from datetime import UTC, datetime

from src.modules.external_fulfillment.domain.error import SupplierFulfillmentTimeError


def normalize_supplier_fulfillment_time(value: datetime) -> datetime:
    """Переводит явно переданный момент с часовым поясом в UTC."""
    if not isinstance(value, datetime):
        raise SupplierFulfillmentTimeError("Нужно время с часовым поясом.")
    try:
        if value.utcoffset() is None:
            raise SupplierFulfillmentTimeError("Нужно время с часовым поясом.")
        return value.astimezone(UTC)
    except (OverflowError, ValueError) as exc:
        raise SupplierFulfillmentTimeError(
            "Время невозможно представить в UTC."
        ) from exc
