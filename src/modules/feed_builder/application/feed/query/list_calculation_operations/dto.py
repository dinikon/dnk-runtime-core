from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalculationOperationDTO:
    """Описывает закрытую операцию и её арность для визуального редактора."""

    code: str
    category: str
    label: str
    min_arguments: int
    max_arguments: int


@dataclass(frozen=True, slots=True)
class ListCalculationOperationsResultDTO:
    """Передаёт возможности и бюджеты текущей версии вычислителя."""

    items: tuple[CalculationOperationDTO, ...]
    engine_version: str
    precision: int
    max_depth: int
    max_nodes: int
    max_rules: int
    max_collection_items: int
