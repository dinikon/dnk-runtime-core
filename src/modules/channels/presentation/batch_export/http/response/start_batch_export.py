from uuid import UUID
from pydantic import BaseModel


class StartBatchExportResponse(BaseModel):
    """Возвращает принятое намерение, не обещая внешней записи."""

    run_id: UUID
