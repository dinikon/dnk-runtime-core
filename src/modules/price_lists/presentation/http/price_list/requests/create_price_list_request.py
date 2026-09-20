from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl


class CreatePriceListRequest(BaseModel):
    """HTTP-входные поля CreatePriceListRequest."""

    title: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl
    source_format: Literal["xml", "yaml", "xlsx"]
    source_preset: Literal["prom_xml"] | None = None
    source_config: dict[str, Any] = Field(default_factory=dict)


__all__ = ["CreatePriceListRequest"]
