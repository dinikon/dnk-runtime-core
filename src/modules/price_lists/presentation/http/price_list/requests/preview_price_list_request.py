from typing import Any, Literal
from pydantic import BaseModel, HttpUrl


class PreviewPriceListRequest(BaseModel):
    """HTTP-входные поля PreviewPriceListRequest."""

    source_url: HttpUrl | None = None
    source_format: Literal["xml", "yaml", "xlsx"] | None = None
    source_preset: Literal["prom_xml"] | None = None
    source_config: dict[str, Any] | None = None
    mapping_config: dict[str, Any] | None = None


__all__ = ["PreviewPriceListRequest"]
