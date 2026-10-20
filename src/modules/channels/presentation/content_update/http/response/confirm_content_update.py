from uuid import UUID
from pydantic import BaseModel


class ConfirmContentUpdateResponse(BaseModel):
    """Возвращает принятую операцию, не обещая завершения внешней записи."""

    run_id: UUID
