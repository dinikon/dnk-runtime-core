from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias
from uuid import UUID

from ..errors import (
    FieldMaxItemsInvalidError,
    FieldOptionCodeRequiredError,
    FieldOptionDuplicateCodeError,
    FieldOptionLabelRequiredError,
    FieldOptionSetCannotBeEmptyError,
    FieldSettingBoundsError,
)
from .value_object import FieldIdVO
from ..object.value_object import ObjectIdVO


@dataclass(frozen=True, slots=True)
class FieldOption:
    code: str
    label: str
    color: str | None = None
    position: int = 0
    is_active: bool = True

    def __post_init__(self) -> None:
        normalized_code = self.code.strip().lower()
        if not normalized_code:
            raise FieldOptionCodeRequiredError()

        normalized_label = self.label.strip()
        if not normalized_label:
            raise FieldOptionLabelRequiredError()

        normalized_color = self.color.strip() if self.color is not None else None
        if normalized_color == "":
            normalized_color = None

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "label", normalized_label)
        object.__setattr__(self, "color", normalized_color)


def _ensure_unique_option_codes(items: tuple[FieldOption, ...]) -> None:
    seen_codes: set[str] = set()
    for item in items:
        if item.code in seen_codes:
            raise FieldOptionDuplicateCodeError(item.code)
        seen_codes.add(item.code)


@dataclass(frozen=True, slots=True)
class SelectFieldOptions:
    items: tuple[FieldOption, ...]
    allow_custom: bool = False

    def __post_init__(self) -> None:
        if not self.items:
            raise FieldOptionSetCannotBeEmptyError("select")
        _ensure_unique_option_codes(self.items)

    def contains(self, code: str) -> bool:
        normalized_code = code.strip().lower()
        return any(item.code == normalized_code for item in self.items)


@dataclass(frozen=True, slots=True)
class MultiSelectFieldOptions:
    items: tuple[FieldOption, ...]
    allow_duplicates: bool = False
    max_items: int | None = None

    def __post_init__(self) -> None:
        if not self.items:
            raise FieldOptionSetCannotBeEmptyError("multi_select")
        _ensure_unique_option_codes(self.items)

        if self.max_items is not None and self.max_items <= 0:
            raise FieldMaxItemsInvalidError()

    def contains(self, code: str) -> bool:
        normalized_code = code.strip().lower()
        return any(item.code == normalized_code for item in self.items)


@dataclass(frozen=True, slots=True)
class StringFieldSettings:
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    trim_whitespace: bool = True

    def __post_init__(self) -> None:
        if self.min_length is not None and self.min_length < 0:
            raise FieldSettingBoundsError("min_length must be greater or equal to zero")
        if self.max_length is not None and self.max_length < 0:
            raise FieldSettingBoundsError("max_length must be greater or equal to zero")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise FieldSettingBoundsError("min_length must be less or equal to max_length")

        normalized_pattern = self.pattern.strip() if self.pattern is not None else None
        if normalized_pattern == "":
            normalized_pattern = None
        object.__setattr__(self, "pattern", normalized_pattern)


@dataclass(frozen=True, slots=True)
class IntegerFieldSettings:
    min_value: int | None = None
    max_value: int | None = None

    def __post_init__(self) -> None:
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise FieldSettingBoundsError("min_value must be less or equal to max_value")


@dataclass(frozen=True, slots=True)
class DateTimeFieldSettings:
    timezone_aware: bool = True


@dataclass(frozen=True, slots=True)
class JsonFieldSettings:
    schema_ref: str | None = None

    def __post_init__(self) -> None:
        normalized_schema_ref = (
            self.schema_ref.strip() if self.schema_ref is not None else None
        )
        if normalized_schema_ref == "":
            normalized_schema_ref = None
        object.__setattr__(self, "schema_ref", normalized_schema_ref)


@dataclass(frozen=True, slots=True)
class RelationFieldSettings:
    on_delete: str = "restrict"
    max_links: int | None = None
    enforce_tenant_scope: bool = True

    def __post_init__(self) -> None:
        normalized_on_delete = self.on_delete.strip().lower()
        if normalized_on_delete not in {"restrict", "set_null", "cascade"}:
            raise FieldSettingBoundsError(
                "on_delete must be one of: restrict, set_null, cascade"
            )
        if self.max_links is not None and self.max_links <= 0:
            raise FieldSettingBoundsError("max_links must be greater than zero")
        object.__setattr__(self, "on_delete", normalized_on_delete)


@dataclass(frozen=True, slots=True)
class StringDefaultValue:
    value: str


@dataclass(frozen=True, slots=True)
class IntegerDefaultValue:
    value: int


@dataclass(frozen=True, slots=True)
class BooleanDefaultValue:
    value: bool


@dataclass(frozen=True, slots=True)
class UuidDefaultValue:
    value: UUID


@dataclass(frozen=True, slots=True)
class DateTimeDefaultValue:
    value: datetime


@dataclass(frozen=True, slots=True)
class JsonDefaultValue:
    value: dict[str, object] | list[object]


@dataclass(frozen=True, slots=True)
class SelectDefaultValue:
    code: str

    def __post_init__(self) -> None:
        normalized_code = self.code.strip().lower()
        if not normalized_code:
            raise FieldOptionCodeRequiredError()
        object.__setattr__(self, "code", normalized_code)


@dataclass(frozen=True, slots=True)
class MultiSelectDefaultValue:
    codes: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_codes = tuple(code.strip().lower() for code in self.codes if code.strip())
        if not normalized_codes:
            raise FieldOptionCodeRequiredError()
        if len(set(normalized_codes)) != len(normalized_codes):
            duplicate_code = next(
                code
                for index, code in enumerate(normalized_codes)
                if code in normalized_codes[:index]
            )
            raise FieldOptionDuplicateCodeError(duplicate_code)
        object.__setattr__(self, "codes", normalized_codes)


@dataclass(frozen=True, slots=True)
class RelationDefaultValue:
    target_object_id: ObjectIdVO
    target_field_id: FieldIdVO | None = None


FieldOptions: TypeAlias = SelectFieldOptions | MultiSelectFieldOptions
FieldSettings: TypeAlias = (
    StringFieldSettings
    | IntegerFieldSettings
    | DateTimeFieldSettings
    | JsonFieldSettings
    | RelationFieldSettings
)
FieldDefaultValue: TypeAlias = (
    StringDefaultValue
    | IntegerDefaultValue
    | BooleanDefaultValue
    | UuidDefaultValue
    | DateTimeDefaultValue
    | JsonDefaultValue
    | SelectDefaultValue
    | MultiSelectDefaultValue
    | RelationDefaultValue
)


__all__ = [
    "BooleanDefaultValue",
    "DateTimeDefaultValue",
    "DateTimeFieldSettings",
    "FieldDefaultValue",
    "FieldOption",
    "FieldOptions",
    "FieldSettings",
    "IntegerDefaultValue",
    "IntegerFieldSettings",
    "JsonDefaultValue",
    "JsonFieldSettings",
    "MultiSelectDefaultValue",
    "MultiSelectFieldOptions",
    "RelationDefaultValue",
    "RelationFieldSettings",
    "SelectDefaultValue",
    "SelectFieldOptions",
    "StringDefaultValue",
    "StringFieldSettings",
    "UuidDefaultValue",
]
