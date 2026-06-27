from typing import Literal

from pydantic import BaseModel


class UpdateProviderConnectionStatusRequestSchema(BaseModel):
    """Pydantic-схема тела запроса смены статуса provider connection."""

    status: Literal["ACTIVE", "DISABLED"]


__all__ = ["UpdateProviderConnectionStatusRequestSchema"]
