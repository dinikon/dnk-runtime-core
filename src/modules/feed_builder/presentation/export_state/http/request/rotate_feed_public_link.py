from pydantic import Field

from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class RotateFeedPublicLinkRequest(ClosedSchema):
    """Принимает версию сохранённых настроек Feed."""

    expected_version: int = Field(ge=1, le=9223372036854775807)
