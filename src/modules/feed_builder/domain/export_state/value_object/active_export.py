from dataclasses import dataclass
from datetime import datetime

from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.export_state.error import InvalidExportStateError
from src.modules.feed_builder.domain.validation import require_datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ActiveExportVO:
    """Ссылается на готовый файл Files и описывает текущую выдачу."""

    file_id: EntityIdVO
    format: ExportFormat
    as_of: datetime
    published_at: datetime

    def __post_init__(self) -> None:
        """Проверяет идентичность файла и последовательность дат."""
        require_datetime(self.as_of, error=InvalidExportStateError)
        require_datetime(self.published_at, error=InvalidExportStateError)
        if (
            not isinstance(self.file_id, EntityIdVO)
            or not isinstance(self.format, ExportFormat)
            or self.as_of > self.published_at
        ):
            raise InvalidExportStateError("Некорректный активный файл.")
