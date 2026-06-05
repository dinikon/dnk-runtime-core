from typing import Literal

from pydantic import BaseModel


class UpdateProviderConnectorStatusRequestSchema(BaseModel):
    """Pydantic-схема тела запроса смены статуса provider connector."""

    status: Literal["ACTIVE", "DISABLED"]


__all__ = ["UpdateProviderConnectorStatusRequestSchema"]
