from src.modules.price_lists.application.price_list.query.preview_schedule_query import (
    PreviewScheduleQuery,
)
from src.modules.price_lists.application.price_list.dto.action_dto import (
    SchedulePreviewDTO,
)


class PreviewScheduleUseCase:
    """Выполняет запрос preview_schedule."""

    def __init__(self, calendar, clock):
        self.calendar = calendar
        self.clock = clock

    async def __call__(self, query: PreviewScheduleQuery):
        """Выполняет сценарий через внедрённые доменные порты."""
        return SchedulePreviewDTO(
            tuple(
                self.calendar.occurrences(
                    query.expression, query.timezone, after=self.clock.now()
                )
            )
        )


__all__ = ["PreviewScheduleUseCase"]
