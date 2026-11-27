from pydantic import BaseModel, ConfigDict, Field

from src.modules.feed_builder.presentation.feed.http.schema.graph import (
    FieldGraphSchema,
)


class PutFeedSchemaRequest(BaseModel):
    """Принимает полное определение графа версии 2 с ожидаемой версией фида."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=1, le=9223372036854775807)
    definition: FieldGraphSchema
