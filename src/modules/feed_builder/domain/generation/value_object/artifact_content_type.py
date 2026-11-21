from dataclasses import dataclass
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError


@dataclass(frozen=True, slots=True)
class ArtifactContentTypeVO:
    """Хранит базовый MIME-тип CSV либо XML без транспортных параметров."""

    value: str

    def __post_init__(self) -> None:
        """Ограничивает тип поддержанными Generic-форматами."""
        if not isinstance(self.value, str) or self.value not in (
            "text/csv",
            "application/xml",
        ):
            raise InvalidGenerationValueError("Нужен text/csv либо application/xml.")
