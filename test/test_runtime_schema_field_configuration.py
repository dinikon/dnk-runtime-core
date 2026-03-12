from __future__ import annotations

import unittest
from datetime import datetime
from uuid import uuid4

from src.modules.runtime_schema.domain.errors import (
    FieldDefaultValueInvalidError,
    FieldMaxItemsInvalidError,
    FieldOptionCodeRequiredError,
    FieldOptionDuplicateCodeError,
    FieldOptionLabelRequiredError,
    FieldOptionSetCannotBeEmptyError,
    FieldSettingBoundsError,
)
from src.modules.runtime_schema.domain.field.configuration import (
    AddressDefaultValue,
    ArrayDefaultValue,
    ArrayFieldSettings,
    ArrayItemTypeVO,
    CurrencyDefaultValue,
    CurrencyFieldSettings,
    DateTimeFieldSettings,
    EmailsDefaultValue,
    EmailsFieldSettings,
    FieldOption,
    FullNameDefaultValue,
    LinksDefaultValue,
    MultiSelectDefaultValue,
    MultiSelectFieldOptions,
    PhonesDefaultValue,
    PhonesFieldSettings,
    RelationFieldSettings,
    SelectDefaultValue,
    SelectFieldOptions,
    StringFieldSettings,
)


class TestFieldConfiguration(unittest.TestCase):
    def test_field_option_validation(self) -> None:
        option = FieldOption(code=" NEW ", label=" New ", color=" ")
        self.assertEqual(option.code, "new")
        self.assertEqual(option.label, "New")
        self.assertIsNone(option.color)

        with self.assertRaises(FieldOptionCodeRequiredError):
            FieldOption(code=" ", label="Label")
        with self.assertRaises(FieldOptionLabelRequiredError):
            FieldOption(code="code", label=" ")

    def test_select_and_multi_select_options(self) -> None:
        with self.assertRaises(FieldOptionSetCannotBeEmptyError):
            SelectFieldOptions(items=tuple())
        with self.assertRaises(FieldOptionSetCannotBeEmptyError):
            MultiSelectFieldOptions(items=tuple())

        item_a = FieldOption(code="A", label="A")
        item_b = FieldOption(code="B", label="B")
        select_options = SelectFieldOptions(items=(item_a, item_b), allow_custom=False)
        self.assertTrue(select_options.contains("a"))

        multi = MultiSelectFieldOptions(items=(item_a, item_b), max_items=2)
        self.assertTrue(multi.contains("b"))
        with self.assertRaises(FieldMaxItemsInvalidError):
            MultiSelectFieldOptions(items=(item_a,), max_items=0)

    def test_string_and_date_time_settings_validation(self) -> None:
        settings = StringFieldSettings(min_length=1, max_length=100, pattern="  ")
        self.assertIsNone(settings.pattern)
        with self.assertRaises(FieldSettingBoundsError):
            StringFieldSettings(min_length=10, max_length=5)

        datetime_settings = DateTimeFieldSettings(timezone_aware=True, require_utc=True)
        self.assertTrue(datetime_settings.require_utc)
        with self.assertRaises(FieldSettingBoundsError):
            DateTimeFieldSettings(timezone_aware=False, require_utc=True)

    def test_relation_and_array_settings_validation(self) -> None:
        relation = RelationFieldSettings(on_delete="CASCADE", max_links=1)
        self.assertEqual(relation.on_delete, "cascade")
        with self.assertRaises(FieldSettingBoundsError):
            RelationFieldSettings(on_delete="invalid")
        with self.assertRaises(FieldSettingBoundsError):
            RelationFieldSettings(max_links=0)

        array = ArrayFieldSettings(item_type=ArrayItemTypeVO.STRING, max_items=3)
        self.assertEqual(array.item_type, ArrayItemTypeVO.STRING)
        with self.assertRaises(FieldMaxItemsInvalidError):
            ArrayFieldSettings(max_items=0)

    def test_currency_settings_and_default_validation(self) -> None:
        settings = CurrencyFieldSettings(
            allowed_currencies=("USD", "EUR"),
            display_scale=2,
        )
        self.assertEqual(len(settings.allowed_currencies or ()), 2)
        with self.assertRaises(FieldSettingBoundsError):
            CurrencyFieldSettings(display_scale=9)
        with self.assertRaises(FieldSettingBoundsError):
            CurrencyFieldSettings(allowed_currencies=tuple())
        with self.assertRaises(FieldSettingBoundsError):
            CurrencyFieldSettings(allowed_currencies=("USD", "usd"))

        default = CurrencyDefaultValue(amount_minor=1000, currency="USD", display_value="10.00")
        self.assertEqual(default.amount_minor, 1000)
        with self.assertRaises(FieldDefaultValueInvalidError):
            CurrencyDefaultValue(amount_minor=True, currency="USD")
        with self.assertRaises(FieldDefaultValueInvalidError):
            CurrencyDefaultValue(amount_minor=100, currency="USD", display_value="broken")

    def test_email_link_phone_defaults_validation(self) -> None:
        emails = EmailsDefaultValue(emails=("USER@MAIL.COM",))
        self.assertEqual(emails.emails, ("user@mail.com",))
        with self.assertRaises(FieldDefaultValueInvalidError):
            EmailsDefaultValue(emails=("not-email",))

        links = LinksDefaultValue(links=("https://example.com",))
        self.assertEqual(links.links, ("https://example.com",))
        with self.assertRaises(FieldDefaultValueInvalidError):
            LinksDefaultValue(links=("ftp://invalid",))

        phones = PhonesDefaultValue(phones=("+1 (555) 123-45-67",))
        self.assertEqual(len(phones.phones), 1)
        with self.assertRaises(FieldDefaultValueInvalidError):
            PhonesDefaultValue(phones=("abc",))

    def test_misc_default_values(self) -> None:
        address = AddressDefaultValue(
            country=" UA ",
            region=" Kyiv ",
            city=" Kyiv ",
            address_line=" Street 1 ",
            post_code=" 01001 ",
        )
        self.assertEqual(address.country, "UA")
        self.assertEqual(address.post_code, "01001")

        array = ArrayDefaultValue(values=(1, "x"))
        self.assertEqual(array.values, (1, "x"))

        fullname = FullNameDefaultValue(last_name="Doe", middle_name="M", first_name="John")
        self.assertEqual(fullname.first_name, "John")

        select = SelectDefaultValue(code=" New ")
        self.assertEqual(select.code, "new")
        with self.assertRaises(FieldOptionCodeRequiredError):
            SelectDefaultValue(code=" ")

        multi = MultiSelectDefaultValue(codes=("A", "b"))
        self.assertEqual(multi.codes, ("a", "b"))
        with self.assertRaises(FieldOptionDuplicateCodeError):
            MultiSelectDefaultValue(codes=("a", "A"))

    def test_collection_settings_validation(self) -> None:
        emails_settings = EmailsFieldSettings(max_items=3)
        phones_settings = PhonesFieldSettings(max_items=3)
        self.assertEqual(emails_settings.max_items, 3)
        self.assertEqual(phones_settings.max_items, 3)
        with self.assertRaises(FieldMaxItemsInvalidError):
            EmailsFieldSettings(max_items=0)
        with self.assertRaises(FieldMaxItemsInvalidError):
            PhonesFieldSettings(max_items=0)


if __name__ == "__main__":
    unittest.main()

