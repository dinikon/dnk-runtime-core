from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.policy.schema_structure import (
    FeedSchemaStructurePolicy,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.export_state.error import InvalidExportStateError

EXPORT_ENGINE_VERSION = 1


@dataclass(frozen=True, slots=True)
class ExportSnapshotVO:
    """Фиксирует схему и настройки одной незавершённой задачи."""

    schema: FeedSchemaVO
    settings: FeedExportSettingsVO
    engine_version: int = EXPORT_ENGINE_VERSION

    def __post_init__(self) -> None:
        """Проверяет типы и структурные инварианты снимка."""
        if (
            not isinstance(self.schema, FeedSchemaVO)
            or not isinstance(self.settings, FeedExportSettingsVO)
            or type(self.engine_version) is not int
            or self.engine_version < 1
        ):
            raise InvalidExportStateError("Некорректный снимок экспорта.")
        object.__setattr__(
            self, "schema", FeedSchemaStructurePolicy.validate(self.schema)
        )
