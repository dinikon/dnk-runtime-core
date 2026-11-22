from src.modules.feed_builder.domain.feed.calculation.error import (
    CalculationDefinitionError,
)

PARAMETER_TYPES: tuple[tuple[str, str], ...] = (
    ("price.regular", "number"),
    ("price.sale", "number"),
    ("price.effective", "number"),
    ("product.sku", "string"),
    ("product.id", "uuid"),
    ("price.purchase", "number"),
    ("product.category_ids", "collection:uuid"),
)
ENGINE_VERSION = "1"
PRECISION = 40


def parameter_type(identifier: str, path: tuple[str | int, ...] = ()) -> str:
    """Разрешает только реально подключённые параметры, включая проверку неисполненных ветвей."""
    for name, kind in PARAMETER_TYPES:
        if name == identifier:
            return kind
    raise CalculationDefinitionError(
        "UNKNOWN_CALCULATION_PARAMETER",
        "Параметр не подключён к вычислителю: " + identifier,
        path=path,
    )
