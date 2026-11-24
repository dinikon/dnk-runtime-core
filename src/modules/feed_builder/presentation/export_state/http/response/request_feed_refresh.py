from datetime import datetime

from pydantic import BaseModel


class RequestFeedRefreshResponse(BaseModel):
    """Подтверждает текущее состояние поставленной задачи."""

    status: str
    requested_at: datetime
