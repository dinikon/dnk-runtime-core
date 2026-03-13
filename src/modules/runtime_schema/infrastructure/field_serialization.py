from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from src.modules.runtime_schema.domain.field.configuration import (
    ActorDefaultValue,
    ActorFieldSettings,
    AddressDefaultValue,
    AddressFieldSettings,
    ArrayDefaultValue,
    ArrayFieldSettings,
    ArrayItemTypeVO,
    BooleanDefaultValue,
    CurrencyDefaultValue,
    CurrencyFieldSettings,
    DateTimeDefaultValue,
    DateTimeFieldSettings,
    EmailsDefaultValue,
    EmailsFieldSettings,
    FieldOption,
    FieldOptions,
    FieldSettings,
    FullNameDefaultValue,
    FullNameFieldSettings,
    IntegerDefaultValue,
    IntegerFieldSettings,
    JsonDefaultValue,
    JsonFieldSettings,
    LinksDefaultValue,
    LinksFieldSettings,
    MultiSelectDefaultValue,
    MultiSelectFieldOptions,
    PhonesDefaultValue,
    PhonesFieldSettings,
    RelationDefaultValue,
    RelationFieldSettings,
    SelectDefaultValue,
    SelectFieldOptions,
    StringDefaultValue,
    StringFieldSettings,
    UuidDefaultValue,
)
from src.modules.runtime_schema.domain.field.value_object import FieldTypeVO
from src.modules.runtime_schema.domain.object.value_object import ObjectIdVO
from src.modules.runtime_schema.domain.field.value_object import FieldIdVO


_SETTINGS_CLASS_BY_TYPE: dict[FieldTypeVO, type[FieldSettings] | None] = {
    FieldTypeVO.ACTOR: ActorFieldSettings,
    FieldTypeVO.ADDRESS: AddressFieldSettings,
    FieldTypeVO.ARRAY: ArrayFieldSettings,
    FieldTypeVO.UUID: None,
    FieldTypeVO.STRING: StringFieldSettings,
    FieldTypeVO.TEXT: StringFieldSettings,
    FieldTypeVO.INTEGER: IntegerFieldSettings,
    FieldTypeVO.BOOLEAN: None,
    FieldTypeVO.CURRENCY: CurrencyFieldSettings,
    FieldTypeVO.DATE_TIME: DateTimeFieldSettings,
    FieldTypeVO.EMAILS: EmailsFieldSettings,
    FieldTypeVO.FULL_NAME: FullNameFieldSettings,
    FieldTypeVO.JSON: JsonFieldSettings,
    FieldTypeVO.LINKS: LinksFieldSettings,
    FieldTypeVO.PHONES: PhonesFieldSettings,
    FieldTypeVO.SELECT: None,
    FieldTypeVO.MULTI_SELECT: None,
    FieldTypeVO.RELATION: RelationFieldSettings,
}


def _to_primitive(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _to_primitive(val) for key, val in asdict(value).items()}
    if isinstance(value, tuple):
        return [_to_primitive(item) for item in value]
    if isinstance(value, list):
        return [_to_primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_primitive(val) for key, val in value.items()}
    return value


def serialize_field_options(options: FieldOptions | None) -> dict[str, object] | None:
    if options is None:
        return None
    return _to_primitive(options)


def serialize_field_settings(settings: FieldSettings | None) -> dict[str, object] | None:
    if settings is None:
        return None
    return _to_primitive(settings)


def serialize_field_default(default_value: object | None) -> dict[str, object] | None:
    if default_value is None:
        return None
    return _to_primitive(default_value)


def deserialize_field_options(
    *,
    field_type: FieldTypeVO,
    payload: dict[str, object] | None,
) -> FieldOptions | None:
    if payload is None:
        return None

    items_payload = payload.get("items", [])
    if not isinstance(items_payload, list):
        raise ValueError("options.items must be list")

    items = tuple(
        FieldOption(
            code=str(item.get("code", "")),
            label=str(item.get("label", "")),
            color=str(item.get("color")) if item.get("color") is not None else None,
            position=int(item.get("position", 0)),
            is_active=bool(item.get("is_active", True)),
        )
        for item in items_payload
        if isinstance(item, dict)
    )

    if field_type == FieldTypeVO.SELECT:
        return SelectFieldOptions(
            items=items,
            allow_custom=bool(payload.get("allow_custom", False)),
        )

    if field_type == FieldTypeVO.MULTI_SELECT:
        max_items_raw = payload.get("max_items")
        return MultiSelectFieldOptions(
            items=items,
            allow_duplicates=bool(payload.get("allow_duplicates", False)),
            max_items=int(max_items_raw) if max_items_raw is not None else None,
        )

    raise ValueError(f"field type '{field_type.value}' does not support options")


def deserialize_field_settings(
    *,
    field_type: FieldTypeVO,
    payload: dict[str, object] | None,
) -> FieldSettings | None:
    if payload is None:
        return None

    settings_cls = _SETTINGS_CLASS_BY_TYPE[field_type]
    if settings_cls is None:
        raise ValueError(f"field type '{field_type.value}' does not support settings")

    values = dict(payload)
    if settings_cls is ArrayFieldSettings and "item_type" in values:
        values["item_type"] = ArrayItemTypeVO(str(values["item_type"]).lower())
    if settings_cls is CurrencyFieldSettings and "allowed_currencies" in values:
        allowed_currencies_raw = values["allowed_currencies"]
        if isinstance(allowed_currencies_raw, list):
            values["allowed_currencies"] = tuple(str(code) for code in allowed_currencies_raw)
    return settings_cls(**values)


def deserialize_field_default(
    *,
    field_type: FieldTypeVO,
    payload: dict[str, object] | None,
) -> object | None:
    if payload is None:
        return None

    if field_type in {FieldTypeVO.STRING, FieldTypeVO.TEXT}:
        return StringDefaultValue(value=str(payload.get("value", "")))
    if field_type == FieldTypeVO.INTEGER:
        return IntegerDefaultValue(value=int(payload.get("value", 0)))
    if field_type == FieldTypeVO.BOOLEAN:
        return BooleanDefaultValue(value=bool(payload.get("value", False)))
    if field_type == FieldTypeVO.UUID:
        return UuidDefaultValue(value=UUID(str(payload.get("value"))))
    if field_type == FieldTypeVO.DATE_TIME:
        raw = payload.get("value")
        if isinstance(raw, str) and raw.strip().lower() == "now":
            value = datetime.now(UTC)
        else:
            value = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))
        return DateTimeDefaultValue(value=value)
    if field_type == FieldTypeVO.JSON:
        if "value" in payload:
            return JsonDefaultValue(value=payload.get("value"))
        # Backward compatibility: allow direct JSON payload without nested "value".
        return JsonDefaultValue(value=payload)
    if field_type == FieldTypeVO.SELECT:
        return SelectDefaultValue(code=str(payload.get("code", "")))
    if field_type == FieldTypeVO.MULTI_SELECT:
        codes_raw = payload.get("codes", [])
        codes = tuple(str(code) for code in codes_raw if str(code).strip())
        return MultiSelectDefaultValue(codes=codes)
    if field_type == FieldTypeVO.RELATION:
        target_object_raw = payload.get("target_object_id")
        target_field_raw = payload.get("target_field_id")
        return RelationDefaultValue(
            target_object_id=ObjectIdVO.from_value(target_object_raw),
            target_field_id=(
                FieldIdVO.from_value(target_field_raw)
                if target_field_raw is not None
                else None
            ),
        )
    if field_type == FieldTypeVO.ACTOR:
        return ActorDefaultValue(user_id=UUID(str(payload.get("user_id"))))
    if field_type == FieldTypeVO.ADDRESS:
        return AddressDefaultValue(
            country=str(payload.get("country", "")),
            region=str(payload.get("region", "")),
            city=str(payload.get("city", "")),
            address_line=str(payload.get("address_line", "")),
            post_code=str(payload.get("post_code", "")),
        )
    if field_type == FieldTypeVO.ARRAY:
        values_raw = payload.get("values", [])
        values = tuple(values_raw) if isinstance(values_raw, list) else tuple()
        return ArrayDefaultValue(values=values)
    if field_type == FieldTypeVO.CURRENCY:
        return CurrencyDefaultValue(
            amount_minor=int(payload.get("amount_minor", 0)),
            currency=str(payload.get("currency", "")),
            display_value=(
                str(payload.get("display_value"))
                if payload.get("display_value") is not None
                else None
            ),
        )
    if field_type == FieldTypeVO.EMAILS:
        emails_raw = payload.get("emails", [])
        return EmailsDefaultValue(emails=tuple(str(value) for value in emails_raw))
    if field_type == FieldTypeVO.FULL_NAME:
        return FullNameDefaultValue(
            last_name=str(payload.get("last_name", "")),
            middle_name=str(payload.get("middle_name", "")),
            first_name=str(payload.get("first_name", "")),
        )
    if field_type == FieldTypeVO.LINKS:
        links_raw = payload.get("links", [])
        return LinksDefaultValue(links=tuple(str(value) for value in links_raw))
    if field_type == FieldTypeVO.PHONES:
        phones_raw = payload.get("phones", [])
        return PhonesDefaultValue(phones=tuple(str(value) for value in phones_raw))
    return None


__all__ = [
    "deserialize_field_default",
    "deserialize_field_options",
    "deserialize_field_settings",
    "serialize_field_default",
    "serialize_field_options",
    "serialize_field_settings",
]
