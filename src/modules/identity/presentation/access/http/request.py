from pydantic import BaseModel
from typing import Literal


class UserAccessRequest(BaseModel):
    role: Literal["admin", "member"] | None = None
    status: Literal["active", "revoked"] | None = None
