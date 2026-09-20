from typing import Any
from pydantic import BaseModel


class MappingRequest(BaseModel):
    """HTTP-входные поля MappingRequest."""

    source_config: dict[str, Any]
    mapping_config: dict[str, Any]


__all__ = ["MappingRequest"]
