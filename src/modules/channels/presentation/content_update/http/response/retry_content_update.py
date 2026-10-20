from uuid import UUID
from pydantic import BaseModel


class RetryContentUpdateResponse(BaseModel):
    """Возвращает принятую операцию, не обещая завершения внешней записи."""

    run_id: UUID
