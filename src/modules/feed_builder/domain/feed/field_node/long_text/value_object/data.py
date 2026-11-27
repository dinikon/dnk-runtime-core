from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar, TYPE_CHECKING
from src.modules.feed_builder.domain.feed.field_node.data import FieldNodeData
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.field_node.value_validation import (
    validate_text_settings,
)
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constraints import (
    TextConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import TextValueDefinition


@dataclass(frozen=True, slots=True)
class LongTextNodeDataVO(FieldNodeData):
    """Неизменяемые настройки длинного текста."""

    kind: ClassVar[FieldValueType] = FieldValueType.TEXT
    value_definition: TextValueDefinition
    constraints: TextConstraintsVO = field(default_factory=TextConstraintsVO)
    locale: LocaleCodeVO | None = None
    fallback_policy: LocaleFallbackPolicyVO | None = None
    transforms: tuple[TransformDefinitionVO, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет собственные текстовые настройки и копирует transforms."""
        transforms = validate_text_settings(
            value_definition=self.value_definition,
            locale=self.locale,
            fallback_policy=self.fallback_policy,
            constraints=self.constraints,
            transforms=self.transforms,
            multiline=True,
            rich_text=self.kind is FieldValueType.RICH_TEXT,
        )
        object.__setattr__(self, "transforms", transforms)
