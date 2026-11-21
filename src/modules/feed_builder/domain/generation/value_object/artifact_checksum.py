from dataclasses import dataclass
import re
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError


@dataclass(frozen=True, slots=True)
class ArtifactChecksumVO:
    """Хранит каноническую шестнадцатеричную контрольную сумму SHA-256."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет готовую checksum без чтения или хеширования файла."""
        if (
            not isinstance(self.value, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.value) is None
        ):
            raise InvalidGenerationValueError(
                "Нужна SHA-256 checksum в нижнем регистре."
            )
