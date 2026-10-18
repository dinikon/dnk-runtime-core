from pydantic import BaseModel, EmailStr, Field
from typing import Literal


class InviteRequest(BaseModel):
    email: EmailStr
    role: Literal["admin", "member"] = "member"


class InvitationOtpRequest(BaseModel):
    invitation_token: str = Field(min_length=32, max_length=128)


class AcceptInvitationRequest(InvitationOtpRequest):
    token: str = Field(min_length=1, max_length=256)
    code: str = Field(min_length=4, max_length=12)
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
