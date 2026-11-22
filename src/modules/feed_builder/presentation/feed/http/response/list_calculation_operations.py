from pydantic import BaseModel


class CalculationOperationResponse(BaseModel):
    """Передаёт операцию, категорию и арность."""

    code: str
    category: str
    label: str
    min_arguments: int
    max_arguments: int


class ListCalculationOperationsResponse(BaseModel):
    """Передаёт возможности и числовые бюджеты текущей версии."""

    items: tuple[CalculationOperationResponse, ...]
    engine_version: str
    precision: int
    max_depth: int
    max_nodes: int
    max_rules: int
    max_collection_items: int
