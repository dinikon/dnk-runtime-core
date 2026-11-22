from typing import Annotated, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema
from src.modules.feed_builder.presentation.feed.http.schema.export_settings import (
    FeedExportSettingsSchema,
)


class PatchFeedRequest(BaseModel):
    """Различает отсутствующие свойства и запрещённый явный null."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=1, le=9223372036854775807)
    name: Annotated[str, Field(min_length=1, max_length=255)] | SkipJsonSchema[None] = (
        None
    )
    code: Annotated[str, Field(min_length=1, max_length=64)] | SkipJsonSchema[None] = (
        None
    )
    export_settings: FeedExportSettingsSchema | SkipJsonSchema[None] = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Запрещает пустой PATCH и null переданных свойств."""
        changed = self.model_fields_set - {"expected_version"}
        if not changed:
            raise ValueError("Нужно передать хотя бы одно изменение.")
        if (
            ("name" in changed and self.name is None)
            or ("code" in changed and self.code is None)
            or ("export_settings" in changed and self.export_settings is None)
        ):
            raise ValueError("Переданное свойство не может быть null.")
        return self
