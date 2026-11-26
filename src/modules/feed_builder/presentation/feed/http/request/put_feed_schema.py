from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.modules.feed_builder.presentation.feed.http.schema.graph import SchemaDocument


class PutFeedSchemaRequest(BaseModel):
    """Принимает пустую схему версии 1 или плоский граф версии 2."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=1, le=9223372036854775807)
    definition: SchemaDocument

    @field_validator("definition", mode="before")
    @classmethod
    def clear_fields(cls, definition: object) -> object:
        """Заменяет поля до проверки вложенной структуры узлов."""
        if not isinstance(definition, dict):
            return definition
        if definition.get("schema_format_version") == 2:
            return definition
        root = definition.get("root")
        if not isinstance(root, dict):
            return definition
        return {**definition, "root": {**root, "fields": []}}
