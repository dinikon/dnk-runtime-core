from uuid import UUID
from pydantic import BaseModel


class StartContentUpdateResponse(BaseModel):
    """Возвращает принятую операцию, не обещая завершения внешней записи."""

    run_id: UUID
