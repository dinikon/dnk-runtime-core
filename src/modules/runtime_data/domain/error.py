from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.modules.shared import DomainError


class RuntimeDataError(DomainError):
    """Базовая доменная ошибка модуля runtime_data."""

    pass


class RuntimeDataValidationError(RuntimeDataError):
    """Ошибка пользовательских данных, не прошедших runtime-валидацию."""

    pass


class RuntimeDataObjectNotFoundError(RuntimeDataError):
    """Ошибка отсутствия runtime-записи объекта."""

    pass


@dataclass(frozen=True)
class RuntimeDataFilterError(RuntimeDataError):
    """Ошибка некорректного фильтра или сортировки runtime-запроса."""

    code: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))
        object.__setattr__(self, "args", (f"{self.code}: {self.message}",))


class RuntimeDataPolicyError(RuntimeDataError):
    """Ошибка нарушения runtime-политики типов или descriptor."""

    pass


class RuntimeDataPersistenceError(RuntimeDataError):
    """Ошибка сохранения или чтения runtime-данных в backend-хранилище."""

    pass
