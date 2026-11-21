from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetStatusTransitionsQuery:
    """Запрашивает согласованную матрицу переходов текущего Domain."""
