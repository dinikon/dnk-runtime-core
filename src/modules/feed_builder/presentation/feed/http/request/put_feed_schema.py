from pydantic import BaseModel, ConfigDict, Field
from src.modules.feed_builder.presentation.feed.http.schema.definition import (
    SchemaDefinition,
)


class PutFeedSchemaRequest(BaseModel):
    """Принимает весь снимок и общую версию Feed, не самостоятельную ревизию draft."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=1, le=9223372036854775807)
    definition: SchemaDefinition
