from dataclasses import dataclass
import re
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.validation import require_text


@dataclass(frozen=True, slots=True)
class GenerationFailureVO:
    """Хранит стабильный код и безопасное описание ошибки без traceback."""

    code: str
    message: str

    def __post_init__(self) -> None:
        """Ограничивает описание; очистку внешних сообщений выполняет вызывающий слой."""
        require_text(self.code, maximum=100, error=InvalidGenerationValueError)
        require_text(self.message, maximum=1000, error=InvalidGenerationValueError)
        if re.fullmatch(r"[a-z][a-z0-9_]*", self.code) is None:
            raise InvalidGenerationValueError("Нужен стабильный код причины ошибки.")
