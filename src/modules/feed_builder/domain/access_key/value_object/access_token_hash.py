from dataclasses import dataclass, field
from src.modules.feed_builder.domain.access_key.error import InvalidAccessKeyValueError


@dataclass(frozen=True, slots=True)
class AccessTokenHashVO:
    """Хранит неизменяемый 32-байтовый digest ключа, скрытый из repr."""

    value: bytes = field(repr=False)

    def __post_init__(self) -> None:
        """Проверяет представление готового SHA-256 digest без вычисления хеша."""
        if not isinstance(self.value, bytes) or len(self.value) != 32:
            raise InvalidAccessKeyValueError("Нужен 32-байтовый digest ключа.")
