from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.runtime_schema.domain import (
    DataSource,
    DataSourceType,
    FieldMetadata,
    FieldType,
    InvalidDataSourceSchemaError,
    InvalidDataSourceTypeError,
    InvalidFieldNameError,
    InvalidFieldTypeError,
    InvalidObjectOwnershipKindError,
    ObjectMetadata,
    ObjectOwnershipKind,
    ObjectOwnershipKindImmutableError,
)


class TestRuntimeSchemaDomainStep2(unittest.TestCase):
    def test_data_source_create_accepts_postgresql_and_generates_uuid_schema(
        self,
    ) -> None:
        now = datetime(2026, 3, 17, tzinfo=UTC)
        data_source = DataSource.create(
            tenant_id=uuid4(),
            source_type=DataSourceType.POSTGRESQL,
            now=now,
        )

        self.assertEqual(data_source.type, DataSourceType.POSTGRESQL)
        self.assertEqual(data_source.created_at, now)
        self.assertEqual(data_source.updated_at, now)
        UUID(data_source.schema)

    def test_data_source_rejects_unsupported_type(self) -> None:
        with self.assertRaises(InvalidDataSourceTypeError):
            DataSource.create(
                tenant_id=uuid4(),
                source_type="mysql",
            )

    def test_data_source_rejects_non_uuid_schema(self) -> None:
        with self.assertRaises(InvalidDataSourceSchemaError):
            DataSource.create(
                tenant_id=uuid4(),
                schema="not-a-uuid",
            )

    def test_field_metadata_accepts_snake_case_name(self) -> None:
        field = FieldMetadata.create(
            object_metadata_id=uuid4(),
            tenant_id=uuid4(),
            field_type=FieldType.STRING,
            name="telegram_handle",
            label="Telegram",
        )

        self.assertEqual(field.name, "telegram_handle")
        self.assertEqual(field.type, FieldType.STRING)

    def test_field_metadata_rejects_invalid_name_formats(self) -> None:
        invalid_names = (
            "CamelCase",
            "with-hyphen",
            "",
            "_starts_with_underscore",
            "a" * 64,
        )

        for invalid_name in invalid_names:
            with self.subTest(name=invalid_name):
                with self.assertRaises(InvalidFieldNameError):
                    FieldMetadata.create(
                        object_metadata_id=uuid4(),
                        tenant_id=uuid4(),
                        field_type=FieldType.STRING,
                        name=invalid_name,
                        label="Label",
                    )

    def test_field_metadata_rejects_unknown_type(self) -> None:
        with self.assertRaises(InvalidFieldTypeError):
            FieldMetadata.create(
                object_metadata_id=uuid4(),
                tenant_id=uuid4(),
                field_type="UNKNOWN",
                name="valid_name",
                label="Label",
            )

    def test_object_metadata_rejects_unknown_ownership_kind(self) -> None:
        with self.assertRaises(InvalidObjectOwnershipKindError):
            ObjectMetadata.create(
                tenant_id=uuid4(),
                data_source_id=uuid4(),
                name_singular="contact",
                name_plural="contacts",
                label_singular="Contact",
                label_plural="Contacts",
                ownership_kind="team",
                allows_custom_fields=True,
            )

    def test_object_metadata_ownership_kind_is_immutable(self) -> None:
        object_metadata = ObjectMetadata.create(
            tenant_id=uuid4(),
            data_source_id=uuid4(),
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )

        object_metadata.assert_ownership_kind_immutable(ObjectOwnershipKind.MODULE)

        with self.assertRaises(ObjectOwnershipKindImmutableError):
            object_metadata.assert_ownership_kind_immutable(
                ObjectOwnershipKind.CUSTOM
            )

    def test_field_metadata_is_immutable(self) -> None:
        field = FieldMetadata.create(
            object_metadata_id=uuid4(),
            tenant_id=uuid4(),
            field_type=FieldType.BOOLEAN,
            name="is_vip",
            label="VIP",
        )

        with self.assertRaises(FrozenInstanceError):
            field.name = "another_name"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
