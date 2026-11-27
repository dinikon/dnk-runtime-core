from typing import Literal

from pydantic import Field

from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class DocumentFieldExportSchema(ClosedSchema):
    """Задаёт контейнер, элемент и размещение объектного выхода."""

    container: str = Field(min_length=1, max_length=128)
    item: str = Field(min_length=1, max_length=128)
    parent: Literal["ROOT", "SHOP"] = "ROOT"
    layout: Literal["FLAT", "NESTED"] = "FLAT"
    parent_attribute: str = Field(default="parentId", min_length=1, max_length=128)


class PublicationFieldExportSchema(ClosedSchema):
    """Выбирает свойство записи, отдаваемое в предложение."""

    value_key: str = Field(min_length=1, max_length=128)
    required: bool = False


class FieldExportSchema(ClosedSchema):
    """Передаёт экспортное имя и явное участие поля."""

    name: str = Field(min_length=1, max_length=128)
    enabled: bool
    xml_placement: Literal["ELEMENT", "ATTRIBUTE"] = "ELEMENT"
    document: DocumentFieldExportSchema | None = None
    publication: PublicationFieldExportSchema | None = None

    def to_document(self) -> JsonObject:
        """Передаёт параметры в кодек без промежуточной сериализации модели."""
        result: JsonObject = {
            "name": self.name,
            "enabled": self.enabled,
            "xml_placement": self.xml_placement,
        }
        if self.document is not None:
            result["document"] = {
                "container": self.document.container,
                "item": self.document.item,
                "parent": self.document.parent,
                "layout": self.document.layout,
                "parent_attribute": self.document.parent_attribute,
            }
        if self.publication is not None:
            result["publication"] = {
                "value_key": self.publication.value_key,
                "required": self.publication.required,
            }
        return result
