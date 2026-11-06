from datetime import UTC, datetime

from src.modules.inventory.domain.fulfillment_plan.error import FulfillmentPlanTimeError


def normalize_fulfillment_time(value: datetime) -> datetime:
    """Нормализует явный aware-момент в UTC без чтения часов и инфраструктуры."""
    if not isinstance(value, datetime):
        raise FulfillmentPlanTimeError("Нужен datetime с часовым поясом.")
    try:
        if value.utcoffset() is None:
            raise FulfillmentPlanTimeError("Время плана должно содержать часовой пояс.")
        return value.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise FulfillmentPlanTimeError(
            "Время плана невозможно представить в UTC."
        ) from exc
