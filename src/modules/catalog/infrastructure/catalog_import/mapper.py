from collections.abc import Mapping
from dataclasses import asdict
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.aggregate import CatalogImport
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
    ImportFieldMapping,
)
from src.modules.catalog.application.catalog_import.read_models import (
    ImportSummaryDTO,
    ImportAnalysisDTO,
)
from src.modules.catalog.application.catalog_import.contracts import (
    SourceField,
    SourceRecord,
)


def configuration_from_values(values: Mapping[str, Any]) -> ImportConfiguration:
    """Восстанавливает проверяемый VO параметров без бизнес-переходов."""
    return ImportConfiguration(
        **{
            **values,
            "mappings": tuple(
                ImportFieldMapping(**m) for m in values.get("mappings", [])
            ),
        }
    )


class CatalogImportMapper:
    """Чистое преобразование между состоянием хранения и агрегатом."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> CatalogImport:
        """Использует явную фабрику восстановления."""
        values = {key: row[key] for key in CatalogImport.__dataclass_fields__}
        for key in ("id", "actor_id", "source_file_id", "job_id"):
            values[key] = EntityIdVO(values[key]) if values[key] is not None else None
        values["configuration"] = configuration_from_values(row["configuration"])
        return CatalogImport.restore(**values)

    @staticmethod
    def to_values(entity: CatalogImport) -> dict[str, Any]:
        """Извлекает значения для INSERT/UPDATE, не выполняя SQL."""
        values = asdict(entity)
        for key in ("id", "actor_id", "source_file_id", "job_id"):
            value = getattr(entity, key)
            values[key] = value.uuid if value is not None else None
        return values


class CatalogImportQueryMapper:
    """Создаёт ограниченные проекции чтения."""

    @staticmethod
    def to_summary(row: Mapping[str, Any]) -> ImportSummaryDTO:
        """Возвращает данные журнала без source URL и файловых координат."""
        return ImportSummaryDTO(
            **{key: row[key] for key in ImportSummaryDTO.__dataclass_fields__}
        )

    @staticmethod
    def to_analysis(value: Mapping[str, Any]) -> ImportAnalysisDTO:
        """Восстанавливает параметры и безопасные текстовые образцы."""
        return ImportAnalysisDTO(
            format=value.get("format", ""),
            encoding=value.get("encoding"),
            delimiter=value.get("delimiter"),
            record_path=value.get("record_path"),
            candidates=tuple(value.get("candidates", [])),
            fields=tuple(SourceField(**v) for v in value.get("fields", [])),
            samples=tuple(SourceRecord(**v) for v in value.get("samples", [])),
            mapped_samples=tuple(value.get("mapped_samples", [])),
            warnings=tuple(value.get("warnings", [])),
        )
