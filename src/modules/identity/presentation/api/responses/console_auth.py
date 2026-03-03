from uuid import UUID

from pydantic import BaseModel


class RequestEmailOtpResponseSchema(BaseModel):
    token: str
    expires_in: int


class ConfirmEmailOtpResponseSchema(BaseModel):
    ok: bool
    user_id: UUID
    tenant_id: UUID


class LogoutCurrentSessionResponseSchema(BaseModel):
    ok: bool
