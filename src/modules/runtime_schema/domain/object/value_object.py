import re
from dataclasses import dataclass
from typing import Self

from ..errors import (
    ObjectLabelRequiredError,
    ObjectNameInvalidFormatError,
    ObjectNameRequiredError,
)
from modules.shared.domain.value_object.entity_id import EntityIdVO


class ObjectIdVO(EntityIdVO): ...


@dataclass(frozen=True, slots=True)
class ObjectNameVO:
    name_singular: str
    name_plural: str

    _SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

    def __post_init__(self) -> None:
        singular = self.name_singular.strip().lower()
        plural = self.name_plural.strip().lower()

        if not singular:
            raise ObjectNameRequiredError("name_singular")
        if not plural:
            raise ObjectNameRequiredError("name_plural")

        if not self._SNAKE_CASE_PATTERN.match(singular):
            raise ObjectNameInvalidFormatError(singular)
        if not self._SNAKE_CASE_PATTERN.match(plural):
            raise ObjectNameInvalidFormatError(plural)

        object.__setattr__(self, "name_singular", singular)
        object.__setattr__(self, "name_plural", plural)

    @classmethod
    def from_singular(
        cls,
        singular: str,
        *,
        plural: str | None = None,
    ) -> Self:
        normalized_singular = singular.strip().lower()
        resolved_plural = plural if plural is not None else f"{normalized_singular}s"
        return cls(name_singular=normalized_singular, name_plural=resolved_plural)


@dataclass(frozen=True, slots=True)
class ObjectLabelVO:
    name_singular: str
    name_plural: str

    def __post_init__(self) -> None:
        singular = self.name_singular.strip()
        plural = self.name_plural.strip()

        if not singular:
            raise ObjectLabelRequiredError("name_singular")
        if not plural:
            raise ObjectLabelRequiredError("name_plural")

        object.__setattr__(self, "name_singular", singular)
        object.__setattr__(self, "name_plural", plural)

    @classmethod
    def from_name(cls, object_name: ObjectNameVO) -> Self:
        return cls(
            name_singular=cls._humanize(object_name.name_singular),
            name_plural=cls._humanize(object_name.name_plural),
        )

    @staticmethod
    def _humanize(value: str) -> str:
        words = value.replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)


__all__ = ["ObjectIdVO", "ObjectLabelVO", "ObjectNameVO"]
