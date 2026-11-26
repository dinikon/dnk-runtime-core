from pydantic import Field

from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class ResetPublicationOverrideRequest(ClosedSchema):
    """Принимает версии редактора поля при возврате к схеме."""

    expected_feed_version: int = Field(strict=False, ge=1, le=9223372036854775807)
    expected_version: int = Field(strict=False, ge=1, le=9223372036854775807)
