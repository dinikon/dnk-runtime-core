from uuid import UUID
from pydantic import BaseModel


class ResumeBatchExportResponse(BaseModel):
    """Возвращает принятое намерение, не обещая внешней записи."""

    run_id: UUID
