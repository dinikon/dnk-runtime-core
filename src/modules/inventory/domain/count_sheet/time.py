from datetime import UTC, datetime

from src.modules.inventory.domain.count_sheet.error import CountSheetTimeError


def normalize_count_sheet_time(value: datetime) -> datetime:
    """Нормализует явный aware-момент ведомости в UTC без обращения к часам."""
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CountSheetTimeError("Нужен datetime с явным часовым поясом.")
    return value.astimezone(UTC)
