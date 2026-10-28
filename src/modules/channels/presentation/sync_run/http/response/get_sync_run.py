"""HTTP-ответ конкретного сценария Channels."""

from pydantic import BaseModel

from src.modules.channels.presentation.sync_run.http.response.fields import (
    SyncRunFields,
)


class GetSyncRunResponse(BaseModel):
    """Не раскрывает документы хранения и данные доступа."""

    sync_run: SyncRunFields
