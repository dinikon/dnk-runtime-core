from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.runtime_schema.domain.errors import (
    DataSourceDsnInvalidError,
    DataSourceSchemaInvalidFormatError,
    DataSourceSchemaRequiredError,
    DataSourceTypeNotSupportedError,
    FieldNameInvalidFormatError,
    FieldNameRequiredError,
    ObjectLabelRequiredError,
    ObjectNameInvalidFormatError,
    ObjectNameRequiredError,
)
from src.modules.runtime_schema.domain.field.value_object import (
    FieldIdVO,
    FieldName,
    FieldTypeVO,
)
from src.modules.runtime_schema.domain.object.value_object import (
    ObjectIdVO,
    ObjectLabelVO,
    ObjectNameVO,
)
from src.modules.runtime_schema.domain.source.value_object import (
    DataSourceDsnVO,
    DataSourceIdVO,
    DataSourceSchemaVO,
    DataSourceTypeVO,
)


class TestRuntimeSchemaValueObjects(unittest.TestCase):
    def test_field_name_normalizes_to_snake_case(self) -> None:
        value = FieldName("  Lead_Title  ")
        self.assertEqual(value.value, "lead_title")
        self.assertEqual(str(value), "lead_title")

    def test_field_name_validation(self) -> None:
        with self.assertRaises(FieldNameRequiredError):
            FieldName("   ")
        with self.assertRaises(FieldNameInvalidFormatError):
            FieldName("Lead Title")

    def test_field_id_from_value(self) -> None:
        raw = uuid4()
        vo = FieldIdVO.from_value(raw)
        self.assertEqual(vo.value, raw)

    def test_field_type_enum_contains_expected(self) -> None:
        self.assertEqual(FieldTypeVO.CURRENCY.value, "currency")
        self.assertEqual(FieldTypeVO.MULTI_SELECT.value, "multi_select")
        self.assertEqual(FieldTypeVO.ACTOR.value, "actor")

    def test_object_name_vo(self) -> None:
        name = ObjectNameVO(name_singular="Lead", name_plural="Leads")
        self.assertEqual(name.name_singular, "lead")
        self.assertEqual(name.name_plural, "leads")

        from_singular = ObjectNameVO.from_singular("Contact")
        self.assertEqual(from_singular.name_singular, "contact")
        self.assertEqual(from_singular.name_plural, "contacts")

        with self.assertRaises(ObjectNameRequiredError):
            ObjectNameVO(name_singular=" ", name_plural="items")
        with self.assertRaises(ObjectNameRequiredError):
            ObjectNameVO(name_singular="item", name_plural=" ")
        with self.assertRaises(ObjectNameInvalidFormatError):
            ObjectNameVO(name_singular="1lead", name_plural="leads")
        with self.assertRaises(ObjectNameInvalidFormatError):
            ObjectNameVO(name_singular="lead", name_plural="lead items")

    def test_object_label_vo(self) -> None:
        label = ObjectLabelVO(name_singular="Lead", name_plural="Leads")
        self.assertEqual(label.name_singular, "Lead")
        self.assertEqual(label.name_plural, "Leads")

        generated = ObjectLabelVO.from_name(
            ObjectNameVO(name_singular="contact_point", name_plural="contact_points")
        )
        self.assertEqual(generated.name_singular, "Contact Point")
        self.assertEqual(generated.name_plural, "Contact Points")

        with self.assertRaises(ObjectLabelRequiredError):
            ObjectLabelVO(name_singular=" ", name_plural="Items")
        with self.assertRaises(ObjectLabelRequiredError):
            ObjectLabelVO(name_singular="Item", name_plural=" ")

    def test_object_and_source_id_vo(self) -> None:
        object_raw = uuid4()
        source_raw = uuid4()
        self.assertEqual(ObjectIdVO.from_value(object_raw).value, object_raw)
        self.assertEqual(DataSourceIdVO.from_value(source_raw).value, source_raw)

    def test_data_source_type_vo(self) -> None:
        self.assertEqual(DataSourceTypeVO.from_value("POSTGRESQL"), DataSourceTypeVO.POSTGRESQL)
        self.assertEqual(DataSourceTypeVO.from_value(DataSourceTypeVO.SQLITE), DataSourceTypeVO.SQLITE)
        with self.assertRaises(DataSourceTypeNotSupportedError):
            DataSourceTypeVO.from_value("oracle")

    def test_data_source_schema_vo(self) -> None:
        schema = DataSourceSchemaVO(" Tenant_Main ")
        self.assertEqual(schema.value, "tenant_main")
        self.assertEqual(str(schema), "tenant_main")
        same = DataSourceSchemaVO.from_value(schema)
        self.assertIs(same, schema)

        with self.assertRaises(DataSourceSchemaRequiredError):
            DataSourceSchemaVO(" ")
        with self.assertRaises(DataSourceSchemaInvalidFormatError):
            DataSourceSchemaVO("1tenant")
        with self.assertRaises(DataSourceSchemaInvalidFormatError):
            DataSourceSchemaVO("a" * 64)

    def test_data_source_dsn_vo(self) -> None:
        pg = DataSourceDsnVO("postgresql://user:pass@localhost:5432/dbname")
        sqlite = DataSourceDsnVO("sqlite:///tmp/test.db")
        self.assertIn("postgresql://", pg.value)
        self.assertIn("sqlite:///", sqlite.value)
        self.assertEqual(str(pg), pg.value)
        self.assertIs(DataSourceDsnVO.from_value(pg), pg)

        with self.assertRaises(DataSourceDsnInvalidError):
            DataSourceDsnVO(" ")
        with self.assertRaises(DataSourceDsnInvalidError):
            DataSourceDsnVO("localhost:5432/dbname")
        with self.assertRaises(DataSourceDsnInvalidError):
            DataSourceDsnVO("postgresql:///missing-host")
        with self.assertRaises(DataSourceDsnInvalidError):
            DataSourceDsnVO("sqlite://")


if __name__ == "__main__":
    unittest.main()
