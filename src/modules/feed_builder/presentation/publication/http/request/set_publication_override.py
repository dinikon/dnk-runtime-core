from pydantic import Field, StrictBool, StrictInt, StrictStr

from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class SetPublicationOverrideRequest(ClosedSchema):
    """Принимает версии редактора и текст либо точную денежную сумму."""

    expected_feed_version: int = Field(ge=1, le=9223372036854775807)
    expected_version: int = Field(ge=1, le=9223372036854775807)
    value: StrictStr | StrictInt | StrictBool
