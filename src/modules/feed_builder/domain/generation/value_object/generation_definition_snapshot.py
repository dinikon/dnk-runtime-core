from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.generation.value_object.calculation_engine_version import (
    CalculationEngineVersionVO,
)


@dataclass(frozen=True, slots=True)
class GenerationDefinitionSnapshotVO:
    """Фиксирует определение схемы, одного формата и семантику вычислений без ревизий."""

    schema: FeedSchemaVO
    export_settings: FeedExportSettingsVO
    calculation_engine_version: CalculationEngineVersionVO

    def __post_init__(self) -> None:
        """Требует типизированные настройки; инварианты состава проверяет агрегат."""
        if (
            not isinstance(self.schema, FeedSchemaVO)
            or not isinstance(self.export_settings, FeedExportSettingsVO)
            or not isinstance(
                self.calculation_engine_version, CalculationEngineVersionVO
            )
        ):
            raise InvalidGenerationValueError(
                "Нужен типизированный снимок определения."
            )
