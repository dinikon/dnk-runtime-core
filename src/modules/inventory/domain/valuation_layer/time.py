from datetime import UTC, datetime

from src.modules.inventory.domain.valuation_layer.error import ValuationLayerTimeError


def normalize_valuation_time(value: datetime) -> datetime:
    """Нормализует явный aware-момент в UTC без чтения часов или внешних настроек."""
    if not isinstance(value, datetime):
        raise ValuationLayerTimeError("Нужен datetime с часовым поясом.")
    try:
        if value.utcoffset() is None:
            raise ValuationLayerTimeError("Время слоя должно содержать часовой пояс.")
        return value.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise ValuationLayerTimeError(
            "Время слоя невозможно представить в UTC."
        ) from exc
