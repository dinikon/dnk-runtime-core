from typing import Literal

from pydantic import Field, field_validator

from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.feed_builder.presentation.feed.http.schema.field_export import (
    FieldExportSchema,
)
from src.modules.feed_builder.presentation.feed.http.schema.legacy_graph import (
    SchemaDefinition,
)
from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class FieldNodeSchema(ClosedSchema):
    """Передаёт идентичность, настройки и серверное описание формы ноды."""

    id: str = Field(min_length=36, max_length=36)
    key: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    typeId: str = Field(min_length=1, max_length=128)
    typeVersion: int = Field(ge=1)
    scope: Literal["offer"]
    forms: JsonObject | None = None
    data: JsonObject
    export: FieldExportSchema
    aiInstruction: str | None = Field(default=None, max_length=10000)


class CategoryTreeSchema(ClosedSchema):
    """Хранит данные локального дерева отдельно от ноды Offer."""

    id: str = Field(min_length=36, max_length=36)
    data: JsonObject


class FieldGraphSchema(ClosedSchema):
    """Передаёт плоский список зарегистрированных нод версии 2."""

    schema_format_version: Literal[2]
    fields: list[FieldNodeSchema] = Field(max_length=MAX_FIELDS)
    categoryTrees: list[CategoryTreeSchema] = Field(
        default_factory=list, max_length=MAX_FIELDS
    )

    @field_validator("schema_format_version", mode="before")
    @classmethod
    def require_version_integer(cls, value: object) -> int:
        """Принимает только целую версию нового графа."""
        if type(value) is not int or value != 2:
            raise ValueError("Поддерживается целая версия графа 2.")
        return value


type SchemaDocument = SchemaDefinition | FieldGraphSchema
