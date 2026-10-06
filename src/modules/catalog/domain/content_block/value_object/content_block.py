import re
from dataclasses import dataclass
from enum import StrEnum

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.content_block.error import InvalidContentBlockError


@dataclass(frozen=True, slots=True)
class ContentBlockIdVO(EntityIdVO):
    pass


@dataclass(frozen=True, slots=True)
class ContentBlockCodeVO:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidContentBlockError("Content block code must be a string.")
        value = self.value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", value):
            raise InvalidContentBlockError("Invalid content block code.")
        object.__setattr__(self, "value", value)


class ContentBlockType(StrEnum):
    TEXT = "text"
    RICH_TEXT = "rich_text"


@dataclass(frozen=True, slots=True)
class ContentBlockTranslationVO:
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not 1 <= len(self.name.strip()) <= 255:
            raise InvalidContentBlockError(
                "Content block name must contain 1–255 characters."
            )
        object.__setattr__(self, "name", self.name.strip())
