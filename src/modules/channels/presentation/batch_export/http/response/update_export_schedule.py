from datetime import datetime
from pydantic import BaseModel


class UpdateExportScheduleResponse(BaseModel):
    """Возвращает новую версию policy и ближайшее исполнение."""

    revision: int
    next_at: datetime | None
