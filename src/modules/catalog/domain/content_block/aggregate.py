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
        if not isinstance(id, ContentBlockIdVO) or not isinstance(
            code, ContentBlockCodeVO
        ):
            raise InvalidContentBlockError("Invalid content block identity.")
        if not isinstance(type, ContentBlockType) or not isinstance(is_system, bool):
            raise InvalidContentBlockError("Invalid content block settings.")
        if not translations:
            raise InvalidContentBlockError("At least one translation is required.")
        if any(
            not isinstance(item, ContentBlockTranslationVO)
            for item in translations.values()
        ):
            raise InvalidContentBlockError("Invalid content block translation.")
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

    def replace_translations(
        self, translations: Mapping[str, ContentBlockTranslationVO]
    ) -> None:
        if not translations or any(
            not isinstance(item, ContentBlockTranslationVO)
            for item in translations.values()
        ):
            raise InvalidContentBlockError(
                "At least one valid translation is required."
            )
        self._translations = dict(translations)

    def change_type(self, value_type: ContentBlockType) -> None:
        if self.is_system:
            raise InvalidContentBlockError(
                "System content block type cannot be changed."
            )
        if not isinstance(value_type, ContentBlockType):
            raise InvalidContentBlockError("Invalid content block type.")
        self.type = value_type
