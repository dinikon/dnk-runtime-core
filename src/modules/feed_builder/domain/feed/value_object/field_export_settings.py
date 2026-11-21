from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class FieldExportSettingsVO:
    """Определяет участие поля в экспорте и безопасное имя результата."""

    name: ExportNameVO
    enabled: bool = True

    def __post_init__(self) -> None:
        """Проверяет тип имени и явный boolean без неявного приведения."""
        if not isinstance(self.name, ExportNameVO) or type(self.enabled) is not bool:
            raise InvalidFeedValueError("Нужны ExportNameVO и bool участия в экспорте.")
