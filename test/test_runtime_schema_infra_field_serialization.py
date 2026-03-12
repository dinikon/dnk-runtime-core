from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.runtime_schema.domain.field.configuration import (
    DateTimeDefaultValue,
    JsonDefaultValue,
    UuidDefaultValue,
    ArrayFieldSettings,
    ArrayItemTypeVO,
    CurrencyDefaultValue,
    CurrencyFieldSettings,
    MultiSelectDefaultValue,
    MultiSelectFieldOptions,
    SelectDefaultValue,
    SelectFieldOptions,
    StringDefaultValue,
)
from src.modules.runtime_schema.domain.field.value_object import FieldTypeVO
from src.modules.runtime_schema.infrastructure.field_serialization import (
    deserialize_field_default,
    deserialize_field_options,
    deserialize_field_settings,
    serialize_field_default,
    serialize_field_options,
    serialize_field_settings,
)


class TestFieldSerialization(unittest.TestCase):
    def test_serialize_deserialize_select_options(self) -> None:
        options = deserialize_field_options(
            field_type=FieldTypeVO.SELECT,
            payload={
                "items": [
                    {"code": "new", "label": "New"},
                    {"code": "won", "label": "Won"},
                ],
                "allow_custom": False,
            },
        )
        self.assertIsInstance(options, SelectFieldOptions)
        serialized = serialize_field_options(options)
        self.assertIsNotNone(serialized)
        self.assertIn("items", serialized or {})

    def test_serialize_deserialize_multi_select_options(self) -> None:
        options = deserialize_field_options(
            field_type=FieldTypeVO.MULTI_SELECT,
            payload={
                "items": [{"code": "a", "label": "A"}],
                "allow_duplicates": False,
                "max_items": 2,
            },
        )
        self.assertIsInstance(options, MultiSelectFieldOptions)
        serialized = serialize_field_options(options)
        self.assertEqual(serialized["max_items"], 2)

    def test_deserialize_settings(self) -> None:
        array_settings = deserialize_field_settings(
            field_type=FieldTypeVO.ARRAY,
            payload={"item_type": "integer", "max_items": 5, "allow_duplicates": False},
        )
        self.assertIsInstance(array_settings, ArrayFieldSettings)
        self.assertEqual(array_settings.item_type, ArrayItemTypeVO.INTEGER)

        currency_settings = deserialize_field_settings(
            field_type=FieldTypeVO.CURRENCY,
            payload={"allowed_currencies": ["USD", "EUR"], "display_scale": 2},
        )
        self.assertIsInstance(currency_settings, CurrencyFieldSettings)
        serialized = serialize_field_settings(currency_settings)
        self.assertEqual(serialized["display_scale"], 2)

    def test_deserialize_default_values(self) -> None:
        self.assertIsInstance(
            deserialize_field_default(
                field_type=FieldTypeVO.STRING,
                payload={"value": "text"},
            ),
            StringDefaultValue,
        )
        self.assertIsInstance(
            deserialize_field_default(
                field_type=FieldTypeVO.SELECT,
                payload={"code": "new"},
            ),
            SelectDefaultValue,
        )
        self.assertIsInstance(
            deserialize_field_default(
                field_type=FieldTypeVO.MULTI_SELECT,
                payload={"codes": ["a", "b"]},
            ),
            MultiSelectDefaultValue,
        )
        self.assertIsInstance(
            deserialize_field_default(
                field_type=FieldTypeVO.CURRENCY,
                payload={"amount_minor": 100, "currency": "USD", "display_value": "1.00"},
            ),
            CurrencyDefaultValue,
        )
        self.assertIsInstance(
            deserialize_field_default(
                field_type=FieldTypeVO.INTEGER,
                payload={"value": 10},
            ).value,
            int,
        )
        self.assertTrue(
            deserialize_field_default(
                field_type=FieldTypeVO.BOOLEAN,
                payload={"value": True},
            ).value
        )
        self.assertIsInstance(
            deserialize_field_default(
                field_type=FieldTypeVO.UUID,
                payload={"value": str(uuid4())},
            ),
            UuidDefaultValue,
        )

    def test_deserialize_json_backward_compatibility(self) -> None:
        nested = deserialize_field_default(
            field_type=FieldTypeVO.JSON,
            payload={"value": {"a": 1}},
        )
        direct = deserialize_field_default(
            field_type=FieldTypeVO.JSON,
            payload={"a": 1},
        )
        self.assertEqual(nested.value, {"a": 1})
        self.assertEqual(direct.value, {"a": 1})

    def test_serialize_default_roundtrip_complex(self) -> None:
        original = CurrencyDefaultValue(amount_minor=1234, currency="USD", display_value="12.34")
        payload = serialize_field_default(original)
        restored = deserialize_field_default(field_type=FieldTypeVO.CURRENCY, payload=payload)
        self.assertEqual(restored.amount_minor, 1234)
        self.assertEqual(str(restored.currency), "USD")

    def test_deserialize_relation_and_datetime(self) -> None:
        relation_default = deserialize_field_default(
            field_type=FieldTypeVO.RELATION,
            payload={
                "target_object_id": str(uuid4()),
                "target_field_id": str(uuid4()),
            },
        )
        self.assertIsNotNone(relation_default.target_object_id)
        self.assertIsNotNone(relation_default.target_field_id)

        dt_default = deserialize_field_default(
            field_type=FieldTypeVO.DATE_TIME,
            payload={"value": datetime.now(UTC).isoformat()},
        )
        self.assertIsNotNone(dt_default.value.tzinfo)

    def test_deserialize_default_values_for_extended_types(self) -> None:
        actor_default = deserialize_field_default(
            field_type=FieldTypeVO.ACTOR,
            payload={"user_id": str(uuid4())},
        )
        address_default = deserialize_field_default(
            field_type=FieldTypeVO.ADDRESS,
            payload={
                "country": "UA",
                "region": "Kyiv",
                "city": "Kyiv",
                "address_line": "Street 1",
                "post_code": "01001",
            },
        )
        array_default = deserialize_field_default(
            field_type=FieldTypeVO.ARRAY,
            payload={"values": ["a", 1]},
        )
        emails_default = deserialize_field_default(
            field_type=FieldTypeVO.EMAILS,
            payload={"emails": ["a@a.com"]},
        )
        full_name_default = deserialize_field_default(
            field_type=FieldTypeVO.FULL_NAME,
            payload={"last_name": "D", "middle_name": "M", "first_name": "F"},
        )
        links_default = deserialize_field_default(
            field_type=FieldTypeVO.LINKS,
            payload={"links": ["https://example.com"]},
        )
        phones_default = deserialize_field_default(
            field_type=FieldTypeVO.PHONES,
            payload={"phones": ["+15550001111"]},
        )
        self.assertIsNotNone(actor_default.user_id)
        self.assertEqual(address_default.country, "UA")
        self.assertEqual(array_default.values, ("a", 1))
        self.assertEqual(emails_default.emails, ("a@a.com",))
        self.assertEqual(full_name_default.first_name, "F")
        self.assertEqual(links_default.links, ("https://example.com",))
        self.assertEqual(phones_default.phones, ("+15550001111",))
        self.assertIsNone(
            deserialize_field_default(
                field_type="unknown",  # type: ignore[arg-type]
                payload={"unexpected": "value"},
            )
        )

    def test_serialize_primitives_with_uuid_datetime_and_lists(self) -> None:
        dt_default = DateTimeDefaultValue(value=datetime.now(UTC))
        dt_payload = serialize_field_default(dt_default)
        self.assertIsInstance(dt_payload["value"], str)

        json_payload = serialize_field_default(JsonDefaultValue(value=[1, 2, 3]))
        self.assertEqual(json_payload["value"], [1, 2, 3])

    def test_unsupported_options_and_settings_raise(self) -> None:
        with self.assertRaises(ValueError):
            deserialize_field_options(
                field_type=FieldTypeVO.SELECT,
                payload={"items": "not-list"},
            )
        with self.assertRaises(ValueError):
            deserialize_field_options(
                field_type=FieldTypeVO.STRING,
                payload={"items": [{"code": "x", "label": "X"}]},
            )
        with self.assertRaises(ValueError):
            deserialize_field_settings(
                field_type=FieldTypeVO.BOOLEAN,
                payload={"anything": True},
            )


if __name__ == "__main__":
    unittest.main()
