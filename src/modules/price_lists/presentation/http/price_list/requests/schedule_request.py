from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl


class ScheduleRequest(BaseModel):
    """HTTP-входные поля ScheduleRequest."""

    cron_expression: str = Field(min_length=5, max_length=128)
    timezone: str = Field(default="Europe/Kyiv", max_length=64)
    new_item_policy: Literal["create", "quarantine", "ignore"] = "create"
    missing_item_policy: Literal[
        "mark_out_of_stock", "mark_missing", "keep_last", "archive"
    ] = "mark_out_of_stock"
    missing_threshold: int = Field(default=2, ge=1, le=100)


__all__ = ["ScheduleRequest"]
