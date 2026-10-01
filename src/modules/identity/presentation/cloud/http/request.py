from pydantic import BaseModel
from typing import Literal


class CloudStartRequest(BaseModel):
    purpose: Literal["login", "link"] = "login"
