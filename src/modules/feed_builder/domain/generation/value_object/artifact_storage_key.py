from dataclasses import dataclass
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.validation import require_text


@dataclass(frozen=True, slots=True)
class ArtifactStorageKeyVO:
    """Хранит непрозрачный внутренний ключ итогового файла без публичного URL."""

    value: str

    def __post_init__(self) -> None:
        """Ограничивает ключ без предположений о конкретном файловом хранилище."""
        require_text(self.value, maximum=1024, error=InvalidGenerationValueError)
