from pydantic import BaseModel, ConfigDict


class RequestModel(BaseModel):
    """Persistence mapping for request."""

    model_config = ConfigDict(extra="forbid")


__all__ = ["RequestModel"]
