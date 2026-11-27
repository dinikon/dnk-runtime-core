from typing import Literal

from pydantic import Field

from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class ChangeFeedAccessModeRequest(ClosedSchema):
    """Передаёт режим скачивания независимо от формата и графа."""

    expected_version: int = Field(ge=1, le=9223372036854775807)
    access_mode: Literal["PUBLIC", "PRIVATE"]
