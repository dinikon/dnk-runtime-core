from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListCalculationParametersQuery:
    """Запрашивает реализованные возможности вычислителя в доверенном контексте."""
