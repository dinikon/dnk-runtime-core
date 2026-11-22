"""Преобразование сохранённых настроек без неявного выбора формата."""

from src.modules.shared.domain.domain_error import DomainError
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.enum.feed_product_mode import FeedProductMode
from src.modules.feed_builder.domain.feed.enum.validation_policy import ValidationPolicy
from src.modules.feed_builder.application.feed.schema_definition import (
    document,
    string,
)
from src.modules.feed_builder.application.feed.schema_error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.infrastructure.feed.persistence.error import (
    InvalidFeedStorageError,
)


def settings_document(value: FeedExportSettingsVO) -> JsonObject:
    """Сохраняет все параметры одного явно выбранного CSV/XML."""
    configuration = value.format_settings
    if isinstance(configuration, CsvExportSettingsVO):
        settings: JsonObject = {
            "format": "csv",
            "delimiter": configuration.delimiter,
            "encoding": configuration.encoding,
            "include_header": configuration.include_header,
        }
    else:
        settings = {
            "format": "xml",
            "root_name": configuration.root_name.value,
            "item_name": configuration.item_name.value,
            "encoding": configuration.encoding,
        }
    return {
        "format_settings": settings,
        "product_mode": value.product_mode.value,
        "validation_policy": value.validation_policy.value,
    }


def settings_from_document(value: object) -> FeedExportSettingsVO:
    """Восстанавливает настройки, отвергая отсутствующий или неизвестный формат."""
    try:
        data = document(value, {"format_settings", "product_mode", "validation_policy"})
        settings = data["format_settings"]
        if not isinstance(settings, dict):
            raise InvalidFeedStorageError("Нужен объект format_settings.")
        if settings.get("format") == "csv":
            settings = document(
                settings, {"format", "delimiter", "encoding", "include_header"}
            )
            configuration = CsvExportSettingsVO(
                delimiter=settings["delimiter"],
                encoding=settings["encoding"],
                include_header=settings["include_header"],
            )
        elif settings.get("format") == "xml":
            settings = document(
                settings, {"format", "root_name", "item_name", "encoding"}
            )
            configuration = XmlExportSettingsVO(
                root_name=ExportNameVO(string(settings["root_name"])),
                item_name=ExportNameVO(string(settings["item_name"])),
                encoding=settings["encoding"],
            )
        else:
            raise InvalidFeedStorageError("Неизвестный формат выгрузки.")
        return FeedExportSettingsVO(
            format_settings=configuration,
            product_mode=FeedProductMode(string(data["product_mode"])),
            validation_policy=ValidationPolicy(string(data["validation_policy"])),
        )
    except (
        DomainError,
        InvalidFeedSchemaDocumentError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise InvalidFeedStorageError(
            "Некорректные сохранённые настройки Feed."
        ) from exc
