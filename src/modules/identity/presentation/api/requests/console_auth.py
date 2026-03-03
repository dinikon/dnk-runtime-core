from pydantic import BaseModel, EmailStr


class RequestEmailOtpRequestSchema(BaseModel):
    email: EmailStr


class ConfirmEmailOtpRequestSchema(BaseModel):
    email: EmailStr
    token: str
    code: str
