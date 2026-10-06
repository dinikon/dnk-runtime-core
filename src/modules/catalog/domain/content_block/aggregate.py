from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockCodeVO,
    ContentBlockIdVO,
    ContentBlockType,
    ContentBlockTranslationVO,
)


class InvalidContentBlockError(ValueError):
    """Нарушен инвариант определения контент-блока."""


@dataclass(eq=False)
class ContentBlockDefinition:
    id: ContentBlockIdVO
    code: ContentBlockCodeVO
    type: ContentBlockType
    is_system: bool = False
    _translations: dict[str, ContentBlockTranslationVO] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        id: ContentBlockIdVO,
        code: ContentBlockCodeVO,
        type: ContentBlockType,
        translations: Mapping[str, ContentBlockTranslationVO],
        is_system: bool = False,
    ) -> "ContentBlockDefinition":
        if not translations:
            raise InvalidContentBlockError("At least one translation is required.")
        return cls(id, code, type, is_system, dict(translations))

    @property
    def translations(self) -> Mapping[str, ContentBlockTranslationVO]:
        return MappingProxyType(self._translations)

    def set_translation(
        self, locale: str, translation: ContentBlockTranslationVO
    ) -> None:
        self._translations[locale] = translation

    def remove_translation(self, locale: str) -> None:
        if locale not in self._translations:
            return
        if len(self._translations) == 1:
            raise InvalidContentBlockError("At least one translation is required.")
        del self._translations[locale]
