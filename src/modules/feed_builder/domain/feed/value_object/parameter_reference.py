from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.validation import text


@dataclass(frozen=True, slots=True)
class ParameterReferenceVO:
    """Ссылается на логический параметр без чтения или проверки внешнего реестра."""

    kind: ClassVar[str] = "parameter"
    parameter: str

    def __post_init__(self) -> None:
        """Проверяет форму идентификатора, не обращаясь к атрибутам Python."""
        object.__setattr__(
            self,
            "parameter",
            text(
                self.parameter,
                label="Parameter",
                maximum=255,
                pattern=r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*",
            ),
        )
