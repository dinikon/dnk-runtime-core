import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.catalog.domain.attribute.error import InvalidAttributeError
from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

_CODE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


def normalize_code(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidAttributeError("Attribute code must be a string.")
    code = value.strip().lower()
    if not _CODE.fullmatch(code):
        raise InvalidAttributeError("Attribute code is invalid.")
    return code


@dataclass(frozen=True, slots=True)
class AttributeContent:
    locale: AttributeLocaleVO
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.locale, AttributeLocaleVO):
            raise InvalidAttributeError("Attribute locale is invalid.")
        if not isinstance(self.name, str) or not 1 <= len(self.name.strip()) <= 255:
            raise InvalidAttributeError("Attribute name must contain 1–255 characters.")
        object.__setattr__(self, "name", self.name.strip())


@dataclass(frozen=True, slots=True)
class AttributeOption:
    id: EntityIdVO
    code: str
    contents: tuple[AttributeContent, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", normalize_code(self.code))
        _unique_locales(self.contents)


def _unique_locales(contents: tuple[AttributeContent, ...]) -> None:
    codes = [content.locale.value for content in contents]
    if len(codes) != len(set(codes)):
        raise InvalidAttributeError("Duplicate attribute content locale.")


@dataclass(frozen=True, slots=True)
class Attribute:
    id: EntityIdVO
    code: str
    options: tuple[AttributeOption, ...]
    contents: tuple[AttributeContent, ...]
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @property
    def type(self) -> str:
        return "SELECT"

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", normalize_code(self.code))
        if not self.options:
            raise InvalidAttributeError("Attribute requires at least one option.")
        _unique_locales(self.contents)
        option_codes = [option.code for option in self.options]
        option_ids: list[UUID] = [option.id.uuid for option in self.options]
        if len(option_codes) != len(set(option_codes)) or len(option_ids) != len(
            set(option_ids)
        ):
            raise InvalidAttributeError("Duplicate attribute option.")

    @classmethod
    def create(
        cls,
        *,
        attribute_id: EntityIdVO,
        code: str,
        options: tuple[AttributeOption, ...],
        contents: tuple[AttributeContent, ...],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> "Attribute":
        return cls(
            id=attribute_id,
            code=code,
            options=options,
            contents=contents,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )
