from dataclasses import dataclass
from datetime import datetime
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.generation.value_object.generation_attempt_token import (
    GenerationAttemptTokenVO,
)
from src.modules.feed_builder.domain.validation import require_datetime, require_integer


@dataclass(frozen=True, slots=True)
class GenerationAttemptVO:
    """Хранит номер и право текущей попытки до заданного срока захвата."""

    number: int
    token: GenerationAttemptTokenVO
    claimed_at: datetime
    lease_until: datetime

    def __post_init__(self) -> None:
        """Проверяет номер, тип токена и положительный интервал захвата без часов."""
        require_integer(self.number, minimum=1, error=InvalidGenerationValueError)
        if not isinstance(self.token, GenerationAttemptTokenVO):
            raise InvalidGenerationValueError("Нужен типизированный токен попытки.")
        require_datetime(self.claimed_at, error=InvalidGenerationValueError)
        require_datetime(self.lease_until, error=InvalidGenerationValueError)
        if self.lease_until <= self.claimed_at:
            raise InvalidGenerationValueError(
                "Срок захвата должен следовать за захватом."
            )
