from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from src.modules.feed_builder.domain.feed.enum.feed_product_mode import FeedProductMode
from src.modules.feed_builder.domain.feed.enum.validation_policy import ValidationPolicy
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import ExportFormatSettings


@dataclass(frozen=True, slots=True)
class FeedExportSettingsVO:
    """Хранит настройки одного явно выбранного формата и режим представления товаров."""

    format_settings: ExportFormatSettings
    validation_policy: ValidationPolicy = ValidationPolicy.STRICT
    product_mode: FeedProductMode = FeedProductMode.VARIABLE_TO_SINGLE

    def __post_init__(self) -> None:
        """Требует настройки CSV либо XML и типизированные режим и политику."""
        if not isinstance(self.product_mode, FeedProductMode):
            raise InvalidFeedValueError("Product Mode должен быть FeedProductMode.")
        if not isinstance(
            self.format_settings, (CsvExportSettingsVO, XmlExportSettingsVO)
        ):
            raise InvalidFeedValueError(
                "Нужны CsvExportSettingsVO либо XmlExportSettingsVO."
            )
        if not isinstance(self.validation_policy, ValidationPolicy):
            raise InvalidFeedValueError("Нужна типизированная validation policy.")
