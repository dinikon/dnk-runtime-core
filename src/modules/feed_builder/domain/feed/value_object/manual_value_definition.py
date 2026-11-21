from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.enum.value_definition_kind import (
    ValueDefinitionKind,
)


@dataclass(frozen=True, slots=True)
class ManualValueDefinitionVO:
    """Определяет ручное заполнение текста без исходного значения в схеме."""

    kind: ClassVar[ValueDefinitionKind] = ValueDefinitionKind.MANUAL
