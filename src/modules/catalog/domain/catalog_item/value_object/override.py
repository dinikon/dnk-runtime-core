from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar
from src.modules.catalog.domain.error import InvalidCatalogValueError

T = TypeVar("T")


class OverrideMode(StrEnum):
    """Различает наследование, собственное значение и явную очистку."""

    INHERIT = "inherit"
    SET = "set"
    CLEAR = "clear"


@dataclass(frozen=True, slots=True)
class OverrideVO(Generic[T]):
    """Неизменяемое явно заданное состояние одного значения или группы."""

    mode: OverrideMode
    value: T | None = None

    def __post_init__(self) -> None:
        """Проверяет согласованность режима и значения, включая false и ноль."""
        if not isinstance(self.mode, OverrideMode) or (
            self.mode == OverrideMode.SET
        ) != (self.value is not None):
            raise InvalidCatalogValueError(
                "Режим переопределения не согласован со значением."
            )
