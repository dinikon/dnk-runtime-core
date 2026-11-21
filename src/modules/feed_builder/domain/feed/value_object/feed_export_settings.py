from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from src.modules.feed_builder.domain.feed.enum.feed_product_mode import FeedProductMode
from src.modules.feed_builder.domain.feed.enum.validation_policy import ValidationPolicy
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.validation import sequence
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import ExportFormatSettings


@dataclass(frozen=True, slots=True)
class FeedExportSettingsVO:
    """Хранит режим представления, форматы и строгую политику без выполнения экспорта."""

    formats: tuple[ExportFormatSettings, ...] = field(
        default_factory=lambda: (CsvExportSettingsVO(), XmlExportSettingsVO())
    )
    validation_policy: ValidationPolicy = ValidationPolicy.STRICT
    product_mode: FeedProductMode = FeedProductMode.VARIABLE_TO_SINGLE

    def __post_init__(self) -> None:
        """Проверяет режим и непустую коллекцию уникальных типизированных форматов."""
        if not isinstance(self.product_mode, FeedProductMode):
            raise InvalidFeedValueError("Product Mode должен быть FeedProductMode.")
        formats = sequence(self.formats, label="Export formats", maximum=2)
        if (
            not formats
            or not all(
                isinstance(value, (CsvExportSettingsVO, XmlExportSettingsVO))
                for value in formats
            )
            or len({value.format for value in formats}) != len(formats)
        ):
            raise InvalidFeedValueError("Нужны неповторяющиеся поддержанные форматы.")
        if not isinstance(self.validation_policy, ValidationPolicy):
            raise InvalidFeedValueError("Нужна типизированная validation policy.")
        object.__setattr__(self, "formats", formats)
