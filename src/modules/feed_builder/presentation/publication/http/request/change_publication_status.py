from pydantic import Field
from typing import Literal
from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class ChangePublicationStatusRequest(ClosedSchema):
    """Принимает версию существующей публикации и допустимое намерение."""

    expected_version: int = Field(ge=1, le=9223372036854775807)
    status: Literal["ENABLED", "PAUSED"]
