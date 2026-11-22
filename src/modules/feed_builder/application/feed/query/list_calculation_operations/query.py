from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListCalculationOperationsQuery:
    """Запрашивает реализованные возможности вычислителя в доверенном контексте."""
