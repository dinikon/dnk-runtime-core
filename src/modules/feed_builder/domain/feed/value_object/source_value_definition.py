from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.enum.value_definition_kind import (
    ValueDefinitionKind,
)
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class SourceValueDefinitionVO:
    """Определяет автоматический текстовый источник без его разрешения."""

    kind: ClassVar[ValueDefinitionKind] = ValueDefinitionKind.SOURCE
    source: SourceReferenceVO

    def __post_init__(self) -> None:
        """Требует типизированную ссылку вместо URL или mutable dict."""
        if not isinstance(self.source, SourceReferenceVO):
            raise InvalidFeedValueError("Нужна SourceReferenceVO.")
