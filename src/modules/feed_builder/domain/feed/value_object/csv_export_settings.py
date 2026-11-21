from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class CsvExportSettingsVO:
    """Хранит параметры универсального CSV без создания сериализатора."""

    format: ClassVar[ExportFormat] = ExportFormat.CSV
    delimiter: str = ","
    encoding: str = "utf-8"
    include_header: bool = True

    def __post_init__(self) -> None:
        """Требует односимвольный разделитель, UTF-8 и boolean заголовка."""
        if (
            not isinstance(self.delimiter, str)
            or len(self.delimiter) != 1
            or self.delimiter in ('"', "\r", "\n", "\x00")
            or not (self.delimiter.isprintable() or self.delimiter == "\t")
        ):
            raise InvalidFeedValueError("Недопустимый разделитель CSV.")
        if self.encoding != "utf-8" or type(self.include_header) is not bool:
            raise InvalidFeedValueError("CSV требует UTF-8 и bool include_header.")
