from typing import Literal

from pydantic import Field

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
