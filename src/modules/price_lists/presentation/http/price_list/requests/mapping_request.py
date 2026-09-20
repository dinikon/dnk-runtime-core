from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl


class MappingRequest(BaseModel):
    """HTTP-входные поля MappingRequest."""

    source_config: dict[str, Any]
    mapping_config: dict[str, Any]


__all__ = ["MappingRequest"]
