from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import re
from typing import TypeAlias
from urllib.parse import urlparse
from uuid import UUID

from modules.shared.domain.value_object.currency import CurrencyCodeVO
from ..errors import (
    FieldDefaultValueInvalidError,
    FieldMaxItemsInvalidError,
    FieldOptionCodeRequiredError,
    FieldOptionDuplicateCodeError,
    FieldOptionLabelRequiredError,
    FieldOptionSetCannotBeEmptyError,
    FieldSettingBoundsError,
)
from ..object.value_object import ObjectIdVO
from .value_object import FieldIdVO

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_ALLOWED_PATTERN = re.compile(r"^\+?[0-9()\-\s]+$")


def _normalize_non_empty(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise FieldDefaultValueInvalidError(f"{field_name} is required")
    return normalized


def _normalize_codes(codes: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    normalized_codes = tuple(code.strip().lower() for code in codes if code.strip())
    if not normalized_codes:
        raise FieldDefaultValueInvalidError(f"{field_name} must not be empty")
    if len(set(normalized_codes)) != len(normalized_codes):
        duplicate_code = next(
            code
            for index, code in enumerate(normalized_codes)
            if code in normalized_codes[:index]
        )
        raise FieldOptionDuplicateCodeError(duplicate_code)
    return normalized_codes


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_phone(value: str) -> str:
    normalized = _normalize_non_empty(value, field_name="phone")
    if not PHONE_ALLOWED_PATTERN.match(normalized):
        raise FieldDefaultValueInvalidError(f"invalid phone '{value}'")

    digits_only = "".join(ch for ch in normalized if ch.isdigit())
    if len(digits_only) < 7 or len(digits_only) > 15:
        raise FieldDefaultValueInvalidError(f"invalid phone '{value}'")

    return normalized


def _normalize_email(value: str) -> str:
    normalized = _normalize_non_empty(value, field_name="email").lower()
    if not EMAIL_PATTERN.match(normalized):
        raise FieldDefaultValueInvalidError(f"invalid email '{value}'")
    return normalized


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


class ArrayItemTypeVO(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    UUID = "uuid"
    DATE_TIME = "date_time"
    NUMBER = "number"


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
    require_utc: bool = True

    def __post_init__(self) -> None:
        if self.require_utc and not self.timezone_aware:
            raise FieldSettingBoundsError(
                "require_utc cannot be true when timezone_aware is false"
            )


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
class ActorFieldSettings:
    enforce_existing_user: bool = True


@dataclass(frozen=True, slots=True)
class AddressFieldSettings:
    require_country: bool = True
    require_region: bool = True
    require_city: bool = True
    require_address_line: bool = True
    require_post_code: bool = True


@dataclass(frozen=True, slots=True)
class ArrayFieldSettings:
    item_type: ArrayItemTypeVO = ArrayItemTypeVO.STRING
    max_items: int | None = None
    allow_duplicates: bool = True

    def __post_init__(self) -> None:
        if self.max_items is not None and self.max_items <= 0:
            raise FieldMaxItemsInvalidError()


@dataclass(frozen=True, slots=True)
class CurrencyFieldSettings:
    allowed_currencies: tuple[CurrencyCodeVO | str, ...] | None = None
    display_scale: int = 2

    def __post_init__(self) -> None:
        if self.display_scale < 0 or self.display_scale > 6:
            raise FieldSettingBoundsError("display_scale must be in range [0, 6]")

        if self.allowed_currencies is None:
            return
        if not self.allowed_currencies:
            raise FieldSettingBoundsError("allowed_currencies must not be empty")

        normalized_codes = tuple(
            CurrencyCodeVO.from_value(code) for code in self.allowed_currencies
        )
        if len(set(normalized_codes)) != len(normalized_codes):
            raise FieldSettingBoundsError("allowed_currencies must not contain duplicates")
        object.__setattr__(self, "allowed_currencies", normalized_codes)


@dataclass(frozen=True, slots=True)
class EmailsFieldSettings:
    max_items: int = 5
    allow_duplicates: bool = False

    def __post_init__(self) -> None:
        if self.max_items <= 0:
            raise FieldMaxItemsInvalidError()


@dataclass(frozen=True, slots=True)
class FullNameFieldSettings:
    require_last_name: bool = True
    require_middle_name: bool = True
    require_first_name: bool = True


@dataclass(frozen=True, slots=True)
class LinksFieldSettings:
    max_items: int = 5
    allow_duplicates: bool = False

    def __post_init__(self) -> None:
        if self.max_items <= 0:
            raise FieldMaxItemsInvalidError()


@dataclass(frozen=True, slots=True)
class PhonesFieldSettings:
    max_items: int = 5
    allow_duplicates: bool = False

    def __post_init__(self) -> None:
        if self.max_items <= 0:
            raise FieldMaxItemsInvalidError()


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
        object.__setattr__(
            self,
            "codes",
            _normalize_codes(self.codes, field_name="multi_select default codes"),
        )


@dataclass(frozen=True, slots=True)
class RelationDefaultValue:
    target_object_id: ObjectIdVO
    target_field_id: FieldIdVO | None = None


@dataclass(frozen=True, slots=True)
class ActorDefaultValue:
    user_id: UUID


@dataclass(frozen=True, slots=True)
class AddressDefaultValue:
    country: str
    region: str
    city: str
    address_line: str
    post_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "country", self.country.strip())
        object.__setattr__(self, "region", self.region.strip())
        object.__setattr__(self, "city", self.city.strip())
        object.__setattr__(self, "address_line", self.address_line.strip())
        object.__setattr__(self, "post_code", self.post_code.strip())


@dataclass(frozen=True, slots=True)
class ArrayDefaultValue:
    values: tuple[object, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", tuple(self.values))


@dataclass(frozen=True, slots=True)
class CurrencyDefaultValue:
    amount_minor: int
    currency: CurrencyCodeVO | str
    display_value: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise FieldDefaultValueInvalidError("amount_minor must be integer")

        normalized_currency = CurrencyCodeVO.from_value(self.currency)

        normalized_display = (
            self.display_value.strip() if self.display_value is not None else None
        )
        if normalized_display == "":
            normalized_display = None

        if normalized_display is not None:
            try:
                Decimal(normalized_display)
            except (InvalidOperation, ValueError):
                raise FieldDefaultValueInvalidError(
                    f"invalid currency display value '{self.display_value}'"
                ) from None

        object.__setattr__(self, "currency", normalized_currency)
        object.__setattr__(self, "display_value", normalized_display)


@dataclass(frozen=True, slots=True)
class EmailsDefaultValue:
    emails: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_emails = tuple(_normalize_email(value) for value in tuple(self.emails))
        object.__setattr__(self, "emails", normalized_emails)


@dataclass(frozen=True, slots=True)
class FullNameDefaultValue:
    last_name: str
    middle_name: str
    first_name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "last_name", self.last_name.strip())
        object.__setattr__(self, "middle_name", self.middle_name.strip())
        object.__setattr__(self, "first_name", self.first_name.strip())


@dataclass(frozen=True, slots=True)
class LinksDefaultValue:
    links: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_links: list[str] = []
        for value in tuple(self.links):
            normalized = _normalize_non_empty(value, field_name="link")
            if not _is_valid_url(normalized):
                raise FieldDefaultValueInvalidError(f"invalid link '{value}'")
            normalized_links.append(normalized)
        object.__setattr__(self, "links", tuple(normalized_links))


@dataclass(frozen=True, slots=True)
class PhonesDefaultValue:
    phones: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_phones = tuple(_normalize_phone(value) for value in tuple(self.phones))
        object.__setattr__(self, "phones", normalized_phones)


FieldOptions: TypeAlias = SelectFieldOptions | MultiSelectFieldOptions
FieldSettings: TypeAlias = (
    ActorFieldSettings
    | AddressFieldSettings
    | ArrayFieldSettings
    | CurrencyFieldSettings
    | DateTimeFieldSettings
    | EmailsFieldSettings
    | FullNameFieldSettings
    | IntegerFieldSettings
    | JsonFieldSettings
    | LinksFieldSettings
    | PhonesFieldSettings
    | RelationFieldSettings
    | StringFieldSettings
)
FieldDefaultValue: TypeAlias = (
    ActorDefaultValue
    | AddressDefaultValue
    | ArrayDefaultValue
    | BooleanDefaultValue
    | CurrencyDefaultValue
    | DateTimeDefaultValue
    | EmailsDefaultValue
    | FullNameDefaultValue
    | IntegerDefaultValue
    | JsonDefaultValue
    | LinksDefaultValue
    | MultiSelectDefaultValue
    | PhonesDefaultValue
    | RelationDefaultValue
    | SelectDefaultValue
    | StringDefaultValue
    | UuidDefaultValue
)


__all__ = [
    "ActorDefaultValue",
    "ActorFieldSettings",
    "AddressDefaultValue",
    "AddressFieldSettings",
    "ArrayDefaultValue",
    "ArrayFieldSettings",
    "ArrayItemTypeVO",
    "BooleanDefaultValue",
    "CurrencyDefaultValue",
    "CurrencyFieldSettings",
    "CurrencyCodeVO",
    "DateTimeDefaultValue",
    "DateTimeFieldSettings",
    "EmailsDefaultValue",
    "EmailsFieldSettings",
    "FieldDefaultValue",
    "FieldOption",
    "FieldOptions",
    "FieldSettings",
    "FullNameDefaultValue",
    "FullNameFieldSettings",
    "IntegerDefaultValue",
    "IntegerFieldSettings",
    "JsonDefaultValue",
    "JsonFieldSettings",
    "LinksDefaultValue",
    "LinksFieldSettings",
    "MultiSelectDefaultValue",
    "MultiSelectFieldOptions",
    "PhonesDefaultValue",
    "PhonesFieldSettings",
    "RelationDefaultValue",
    "RelationFieldSettings",
    "SelectDefaultValue",
    "SelectFieldOptions",
    "StringDefaultValue",
    "StringFieldSettings",
    "UuidDefaultValue",
]
