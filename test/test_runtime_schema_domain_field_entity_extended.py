from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

from src.modules.runtime_schema.domain.errors import (
    FieldDefaultOptionNotFoundError,
    FieldDefaultRelationTargetMismatchError,
    FieldDefaultTypeMismatchError,
    FieldDefaultValueInvalidError,
    FieldLabelRequiredError,
    FieldOptionsRequiredError,
    FieldRelationTargetNotAllowedError,
    FieldSettingsTypeMismatchError,
)
from src.modules.runtime_schema.domain.field.configuration import (
    AddressDefaultValue,
    AddressFieldSettings,
    ArrayDefaultValue,
    ArrayFieldSettings,
    ArrayItemTypeVO,
    CurrencyDefaultValue,
    CurrencyFieldSettings,
    DateTimeDefaultValue,
    DateTimeFieldSettings,
    EmailsDefaultValue,
    EmailsFieldSettings,
    FieldOption,
    FullNameDefaultValue,
    FullNameFieldSettings,
    IntegerDefaultValue,
    LinksDefaultValue,
    LinksFieldSettings,
    MultiSelectDefaultValue,
    MultiSelectFieldOptions,
    PhonesDefaultValue,
    PhonesFieldSettings,
    RelationDefaultValue,
    SelectDefaultValue,
    SelectFieldOptions,
    StringDefaultValue,
    StringFieldSettings,
)
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import (
    FieldIdVO,
    FieldName,
    FieldTypeVO,
)
from src.modules.runtime_schema.domain.object.value_object import ObjectIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def _tenant_id() -> EntityIdVO:
    return EntityIdVO.from_value(uuid4())


def _object_id() -> ObjectIdVO:
    return ObjectIdVO.from_value(uuid4())


def _field_id() -> FieldIdVO:
    return FieldIdVO.from_value(uuid4())


class TestDomainFieldEntityExtended(unittest.TestCase):
    def test_setters_touch_and_rollbacks(self) -> None:
        entity = FieldMetadataEntity.create(
            tenant_id=_tenant_id(),
            object_metadata_id=_object_id(),
            field_type=FieldTypeVO.STRING,
            field_name=FieldName("title"),
            label=" Title ",
            description=" ",
            icon=" ",
            settings=StringFieldSettings(min_length=1, max_length=10),
            default_value=StringDefaultValue(value="abc"),
        )
        self.assertEqual(entity.label, "Title")
        self.assertIsNone(entity.description)
        self.assertIsNone(entity.icon)

        previous_updated_at = entity.updated_at
        entity.set_settings(StringFieldSettings(min_length=1, max_length=20))
        self.assertGreaterEqual(entity.updated_at, previous_updated_at)

        previous_default = entity.default_value
        with self.assertRaises(FieldDefaultTypeMismatchError):
            entity.set_default_value(IntegerDefaultValue(value=1))
        self.assertEqual(entity.default_value, previous_default)

        previous_target_object = entity.relation_target_object_id
        with self.assertRaises(FieldRelationTargetNotAllowedError):
            entity.set_relation_target(target_object_id=_object_id())
        self.assertEqual(entity.relation_target_object_id, previous_target_object)

        select_entity = FieldMetadataEntity.create(
            tenant_id=_tenant_id(),
            object_metadata_id=_object_id(),
            field_type=FieldTypeVO.SELECT,
            field_name=FieldName("status"),
            label="Status",
            is_index=True,
            options=SelectFieldOptions(items=(FieldOption(code="new", label="New"),)),
            default_value=SelectDefaultValue(code="new"),
        )
        previous_updated = select_entity.updated_at
        select_entity.set_options(
            SelectFieldOptions(items=(FieldOption(code="new", label="New"),)),
        )
        self.assertGreaterEqual(select_entity.updated_at, previous_updated)

    def test_address_currency_and_datetime_default_contracts(self) -> None:
        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.ADDRESS,
                field_name=FieldName("shipping_address"),
                label="Shipping Address",
                settings=AddressFieldSettings(require_country=True),
                default_value=AddressDefaultValue(
                    country="",
                    region="Kyiv",
                    city="Kyiv",
                    address_line="Street 1",
                    post_code="01001",
                ),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.CURRENCY,
                field_name=FieldName("budget"),
                label="Budget",
                settings=CurrencyFieldSettings(allowed_currencies=("USD",), display_scale=2),
                default_value=CurrencyDefaultValue(
                    amount_minor=1000,
                    currency="EUR",
                    display_value="10.00",
                ),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.CURRENCY,
                field_name=FieldName("amount"),
                label="Amount",
                settings=CurrencyFieldSettings(display_scale=2),
                default_value=CurrencyDefaultValue(
                    amount_minor=1050,
                    currency="USD",
                    display_value="10.500",
                ),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.DATE_TIME,
                field_name=FieldName("planned_at"),
                label="Planned At",
                settings=DateTimeFieldSettings(timezone_aware=False, require_utc=False),
                default_value=DateTimeDefaultValue(value=datetime.now(UTC)),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.DATE_TIME,
                field_name=FieldName("run_at"),
                label="Run At",
                settings=DateTimeFieldSettings(timezone_aware=True, require_utc=True),
                default_value=DateTimeDefaultValue(
                    value=datetime(2025, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
                ),
            )

    def test_collection_defaults_and_relation_contract(self) -> None:
        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.EMAILS,
                field_name=FieldName("emails"),
                label="Emails",
                settings=EmailsFieldSettings(max_items=1, allow_duplicates=False),
                default_value=EmailsDefaultValue(
                    emails=("one@example.com", "one@example.com"),
                ),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.LINKS,
                field_name=FieldName("links"),
                label="Links",
                settings=LinksFieldSettings(max_items=1, allow_duplicates=False),
                default_value=LinksDefaultValue(
                    links=("https://example.com", "https://example.com"),
                ),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.PHONES,
                field_name=FieldName("phones"),
                label="Phones",
                settings=PhonesFieldSettings(max_items=1, allow_duplicates=False),
                default_value=PhonesDefaultValue(phones=("+15551234567", "+15551234567")),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.ARRAY,
                field_name=FieldName("numbers"),
                label="Numbers",
                settings=ArrayFieldSettings(
                    item_type=ArrayItemTypeVO.INTEGER,
                    allow_duplicates=False,
                ),
                default_value=ArrayDefaultValue(values=(1, 1)),
            )

        target_object_id = _object_id()
        target_field_id = _field_id()
        with self.assertRaises(FieldDefaultRelationTargetMismatchError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.RELATION,
                field_name=FieldName("owner_id"),
                label="Owner",
                relation_target_object_id=target_object_id,
                relation_target_field_id=target_field_id,
                default_value=RelationDefaultValue(
                    target_object_id=target_object_id,
                    target_field_id=_field_id(),
                ),
            )

        with self.assertRaises(FieldDefaultOptionNotFoundError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.MULTI_SELECT,
                field_name=FieldName("tags"),
                label="Tags",
                options=MultiSelectFieldOptions(
                    items=(FieldOption(code="a", label="A"),),
                    allow_duplicates=False,
                ),
                default_value=MultiSelectDefaultValue(codes=("a", "b")),
            )

    def test_additional_creation_validation_edges(self) -> None:
        with self.assertRaises(FieldLabelRequiredError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("title"),
                label=" ",
            )

        with self.assertRaises(FieldOptionsRequiredError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.MULTI_SELECT,
                field_name=FieldName("tags"),
                label="Tags",
                options=None,
            )

        with self.assertRaises(FieldSettingsTypeMismatchError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.UUID,
                field_name=FieldName("token"),
                label="Token",
                settings=StringFieldSettings(min_length=1, max_length=5),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=_tenant_id(),
                object_metadata_id=_object_id(),
                field_type=FieldTypeVO.FULL_NAME,
                field_name=FieldName("full_name"),
                label="Full Name",
                settings=FullNameFieldSettings(require_first_name=True),
                default_value=FullNameDefaultValue(
                    last_name="Doe",
                    middle_name="Middle",
                    first_name="",
                ),
            )

    def test_array_item_validator_and_fraction_digits(self) -> None:
        self.assertTrue(
            FieldMetadataEntity._is_array_item_valid(
                item="x",
                item_type=ArrayItemTypeVO.STRING,
            )
        )
        self.assertTrue(
            FieldMetadataEntity._is_array_item_valid(
                item=True,
                item_type=ArrayItemTypeVO.BOOLEAN,
            )
        )
        self.assertTrue(
            FieldMetadataEntity._is_array_item_valid(
                item=str(uuid4()),
                item_type=ArrayItemTypeVO.UUID,
            )
        )
        self.assertFalse(
            FieldMetadataEntity._is_array_item_valid(
                item="not-uuid",
                item_type=ArrayItemTypeVO.UUID,
            )
        )
        self.assertTrue(
            FieldMetadataEntity._is_array_item_valid(
                item=datetime.now(UTC),
                item_type=ArrayItemTypeVO.DATE_TIME,
            )
        )
        self.assertTrue(
            FieldMetadataEntity._is_array_item_valid(
                item=10.5,
                item_type=ArrayItemTypeVO.NUMBER,
            )
        )
        self.assertFalse(
            FieldMetadataEntity._is_array_item_valid(
                item=1,
                item_type="unknown",  # type: ignore[arg-type]
            )
        )
        self.assertEqual(FieldMetadataEntity._fraction_digits("10"), 0)
        self.assertEqual(FieldMetadataEntity._fraction_digits("10.500"), 3)


if __name__ == "__main__":
    unittest.main()
