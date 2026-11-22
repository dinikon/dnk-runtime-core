from pydantic import Field

from src.modules.feed_builder.presentation.feed.http.schema.definition import (
    ClosedSchema,
)


class RestorePublicationRequest(ClosedSchema):
    """Принимает версию существующей публикации и допустимое намерение."""

    expected_version: int = Field(ge=1, le=9223372036854775807)
