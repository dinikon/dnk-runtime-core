from typing import Any, Literal
from pydantic import Field, HttpUrl
from src.modules.price_lists.presentation.http.price_list.requests.schedule_request import (
    ScheduleRequest,
)


class UpdatePriceListSettingsRequest(ScheduleRequest):
    """HTTP-входные поля UpdatePriceListSettingsRequest."""

    title: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl | None = None
    source_format: Literal["xml", "yaml", "xlsx"]
    source_preset: Literal["prom_xml"] | None = None
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]


__all__ = ["UpdatePriceListSettingsRequest"]
