from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PreviewScheduleQuery:
    """Параметры запроса preview_schedule."""

    expression: str
    timezone: str


__all__ = ["PreviewScheduleQuery"]
