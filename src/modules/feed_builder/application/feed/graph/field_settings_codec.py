from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.truncate_parameters import (
    TruncateParametersVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_ceil_step_parameters import (
    MoneyCeilStepParametersVO,
)
from src.modules.feed_builder.application.feed.graph.json_values import (
    document,
    decimal_value,
    integer,
    string,
)


def decode_source(value: object) -> SourceReferenceVO:
    """Восстанавливает закрытую пару provider/path."""
    data = document(value, {"provider", "path"})
    return SourceReferenceVO(
        SourceProvider(string(data["provider"])),
        CatalogSourcePath(string(data["path"])),
    )


def decode_transform(value: object) -> TransformDefinitionVO:
    """Восстанавливает конкретный тип параметров преобразования."""
    data = document(value, {"op", "params"})
    operation = TransformOperation(string(data["op"]))
    if operation is TransformOperation.STRING_TRIM:
        document(data["params"], set())
        parameters = None
    elif operation is TransformOperation.STRING_TRUNCATE:
        params = document(data["params"], {"max_length"})
        parameters = TruncateParametersVO(integer(params["max_length"]))
    else:
        params = document(data["params"], {"step"})
        parameters = MoneyCeilStepParametersVO(decimal_value(params["step"]))
    return TransformDefinitionVO(operation, parameters)


def source_document(source: SourceReferenceVO) -> JsonObject:
    """Представляет типизированный прямой источник без чтения данных."""
    return {"provider": source.provider.value, "path": source.path.value}


def transform_document(value: TransformDefinitionVO) -> JsonObject:
    """Представляет параметры преобразования без выполнения."""
    parameters: JsonObject = {}
    if isinstance(value.parameters, TruncateParametersVO):
        parameters = {"max_length": value.parameters.max_length}
    elif isinstance(value.parameters, MoneyCeilStepParametersVO):
        parameters = {"step": str(value.parameters.step)}
    return {"op": value.operation.value, "params": parameters}
