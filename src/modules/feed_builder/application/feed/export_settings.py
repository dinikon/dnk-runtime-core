"""Чистое преобразование настроек сценария в Domain и обратно."""

from src.modules.feed_builder.application.feed.export_settings_dto import (
    CsvExportSettingsDTO,
    XmlExportSettingsDTO,
    FeedExportSettingsDTO,
)
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
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


def settings_from_dto(value: FeedExportSettingsDTO) -> FeedExportSettingsVO:
    """Создаёт настройки через собственные проверки существующих VO."""
    if not isinstance(value, FeedExportSettingsDTO):
        raise InvalidFeedValueError("Нужны типизированные настройки сценария.")
    configuration = value.format_settings
    if isinstance(configuration, CsvExportSettingsDTO):
        format_settings = CsvExportSettingsVO(
            delimiter=configuration.delimiter,
            encoding=configuration.encoding,
            include_header=configuration.include_header,
        )
    elif isinstance(configuration, XmlExportSettingsDTO):
        format_settings = XmlExportSettingsVO(
            root_name=ExportNameVO(configuration.root_name),
            item_name=ExportNameVO(configuration.item_name),
            encoding=configuration.encoding,
        )
    else:
        raise InvalidFeedValueError("Нужны настройки CSV либо XML.")
    try:
        product_mode = FeedProductMode(value.product_mode)
        validation_policy = ValidationPolicy(value.validation_policy)
    except (ValueError, TypeError) as exc:
        raise InvalidFeedValueError("Неизвестный режим или политика выгрузки.") from exc
    return FeedExportSettingsVO(
        format_settings=format_settings,
        product_mode=product_mode,
        validation_policy=validation_policy,
    )


def settings_to_dto(value: FeedExportSettingsVO) -> FeedExportSettingsDTO:
    """Возвращает данные результата без передачи Domain VO в HTTP."""
    configuration = value.format_settings
    if isinstance(configuration, CsvExportSettingsVO):
        format_settings = CsvExportSettingsDTO(
            delimiter=configuration.delimiter,
            encoding=configuration.encoding,
            include_header=configuration.include_header,
        )
    else:
        format_settings = XmlExportSettingsDTO(
            root_name=configuration.root_name.value,
            item_name=configuration.item_name.value,
            encoding=configuration.encoding,
        )
    return FeedExportSettingsDTO(
        format_settings=format_settings,
        product_mode=value.product_mode.value,
        validation_policy=value.validation_policy.value,
    )
