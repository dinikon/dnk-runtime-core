from datetime import datetime

from pydantic import AwareDatetime, Field, field_validator

from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class IssueFeedAccessKeyRequest(ClosedSchema):
    """Принимает название и срок действия с явно заданной временной зоной."""

    name: str = Field(min_length=1, max_length=120)
    expires_at: AwareDatetime | None = None

    @field_validator("expires_at", mode="before")
    @classmethod
    def parse_expiry(cls, value: object) -> datetime | None:
        """Принимает дату ISO 8601, которую Pydantic проверит на наличие зоны."""
        if value is None:
            return None
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise ValueError("Срок действия передаётся строкой ISO 8601.")
