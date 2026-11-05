from datetime import UTC, datetime

from src.modules.inventory.domain.inventory_count.error import InventoryCountTimeError


def normalize_inventory_count_time(value: datetime) -> datetime:
    """Нормализует явное aware-время инвентаризации в UTC без обращения к часам."""
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InventoryCountTimeError("Нужен datetime с явным часовым поясом.")
    return value.astimezone(UTC)
