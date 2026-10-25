from dataclasses import replace
from src.modules.catalog.application.catalog_import.contracts import (
    SourceDescription,
    SourceField,
    SourceRecord,
)
from src.modules.catalog.application.catalog_import.read_models import ImportAnalysisDTO
from src.modules.catalog.application.catalog_import.auto_mapping import suggest_mappings
from src.modules.catalog.application.catalog_import.values import (
    mapped_values,
    product_values,
    scalar,
    stock_status_value,
)
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.domain.error import CatalogError, InvalidCatalogValueError


def build_import_analysis(
    description: SourceDescription,
    field_list: tuple[SourceField, ...],
    samples: tuple[SourceRecord, ...],
    initial_configuration: ImportConfiguration,
) -> tuple[ImportConfiguration, ImportAnalysisDTO]:
    """Собирает предложения сопоставления и ограниченные предупреждения предпросмотра."""
    configuration = initial_configuration
    if not configuration.mappings:
        configuration = replace(
            configuration,
            mappings=suggest_mappings(field_list, configuration.default_locale),
        )
    allowed = {field.id for field in field_list}
    if any(
        m.source is not None and m.source not in allowed for m in configuration.mappings
    ):
        raise InvalidCatalogValueError(
            "Сопоставленное поле отсутствует в выбранном источнике."
        )
    configuration = replace(
        configuration,
        encoding=description.encoding,
        delimiter=description.delimiter,
        record_path=description.record_path,
    )
    mapped = [mapped_values(configuration, sample.values) for sample in samples]
    warnings: list[str] = []
    for sample, values in zip(samples, mapped):
        try:
            prepared = product_values(configuration, values)
            if "stock_status" in values and "stock_quantity" in values:
                manual = scalar(values, "stock_status")
                if (
                    manual is not None
                    and stock_status_value(manual)
                    != prepared.product.stock.effective_status().value
                ):
                    warnings.append(
                        f"Запись {sample.number}: количество имеет приоритет над наличием."
                    )
        except CatalogError as error:
            warnings.append(f"Запись {sample.number}: {error}")
    analysis = ImportAnalysisDTO(
        format=description.format,
        encoding=description.encoding,
        delimiter=description.delimiter,
        record_path=description.record_path,
        candidates=description.candidates,
        fields=field_list,
        samples=samples,
        mapped_samples=tuple(mapped),
        warnings=tuple(warnings[:20]),
    )
    return configuration, analysis
