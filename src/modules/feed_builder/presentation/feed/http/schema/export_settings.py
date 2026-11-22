from typing import Annotated, Literal, Self
from pydantic import BaseModel, ConfigDict, Field
from src.modules.feed_builder.application.feed.export_settings_dto import (
    CsvExportSettingsDTO,
    XmlExportSettingsDTO,
    FeedExportSettingsDTO,
)


class CsvExportSettingsSchema(BaseModel):
    """Описывает параметры выбранного CSV, исключая XML-свойства."""

    model_config = ConfigDict(extra="forbid", strict=True)
    format: Literal["csv"]
    delimiter: str = ","
    encoding: Literal["utf-8"] = "utf-8"
    include_header: bool = True


class XmlExportSettingsSchema(BaseModel):
    """Описывает параметры выбранного XML, исключая CSV-свойства."""

    model_config = ConfigDict(extra="forbid", strict=True)
    format: Literal["xml"]
    root_name: str = "catalog"
    item_name: str = "product"
    encoding: Literal["utf-8"] = "utf-8"


class FeedExportSettingsSchema(BaseModel):
    """Передаёт одно обязательное описание формата с фиксированными режимами."""

    model_config = ConfigDict(extra="forbid", strict=True)
    format_settings: Annotated[
        CsvExportSettingsSchema | XmlExportSettingsSchema, Field(discriminator="format")
    ]
    product_mode: Literal["VARIABLE_TO_SINGLE"] = "VARIABLE_TO_SINGLE"
    validation_policy: Literal["STRICT"] = "STRICT"

    def to_dto(self) -> FeedExportSettingsDTO:
        """Переводит транспортные значения в контракт сценария."""
        value = self.format_settings
        if isinstance(value, CsvExportSettingsSchema):
            settings = CsvExportSettingsDTO(
                delimiter=value.delimiter,
                encoding=value.encoding,
                include_header=value.include_header,
            )
        else:
            settings = XmlExportSettingsDTO(
                root_name=value.root_name,
                item_name=value.item_name,
                encoding=value.encoding,
            )
        return FeedExportSettingsDTO(
            format_settings=settings,
            product_mode=self.product_mode,
            validation_policy=self.validation_policy,
        )

    @classmethod
    def from_dto(cls, value: FeedExportSettingsDTO) -> Self:
        """Явно формирует HTTP-значения выбранного варианта настроек."""
        configuration = value.format_settings
        if isinstance(configuration, CsvExportSettingsDTO):
            settings = CsvExportSettingsSchema(
                format="csv",
                delimiter=configuration.delimiter,
                encoding=configuration.encoding,
                include_header=configuration.include_header,
            )
        else:
            settings = XmlExportSettingsSchema(
                format="xml",
                root_name=configuration.root_name,
                item_name=configuration.item_name,
                encoding=configuration.encoding,
            )
        return cls(
            format_settings=settings,
            product_mode=value.product_mode,
            validation_policy=value.validation_policy,
        )
