from uuid import UUID

from pydantic import BaseModel


class ConfirmEmailOtpResponseSchema(BaseModel):
    """Pydantic-схема ответа подтверждения email OTP."""

    ok: bool
    user_id: UUID
    tenant_id: UUID


__all__ = ["ConfirmEmailOtpResponseSchema"]
