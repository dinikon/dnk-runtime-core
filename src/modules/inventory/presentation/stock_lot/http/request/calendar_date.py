from datetime import date
import re


def parse_calendar_date(value: object) -> date | None:
    """Преобразует только null или строку YYYY-MM-DD без времени и неявного coercion."""
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None
    ):
        raise ValueError("Укажите календарную дату YYYY-MM-DD без времени.")
    return date.fromisoformat(value)
