from pydantic import BaseModel
from uuid import UUID


class ConfirmEmailOtpResponseSchema(BaseModel):
    """Pydantic-схема ответа подтверждения email OTP."""

    ok: bool
    user_id: UUID
    tenant_id: UUID
