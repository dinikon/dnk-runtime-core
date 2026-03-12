from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.runtime_schema.domain.errors import (
    DataSourceRemoteDsnRequiredError,
    DataSourceTimestampOrderError,
    FieldDefaultExceedsMaxItemsError,
    FieldDefaultOptionNotFoundError,
    FieldDefaultValueInvalidError,
    FieldOptionsNotAllowedError,
    FieldOptionsRequiredError,
    FieldRelationTargetNotAllowedError,
    FieldRelationTargetRequiredError,
    FieldSystemCustomFlagsInvalidError,
    FieldTimestampOrderError,
    FieldUniqueMustBeIndexedError,
    ObjectSystemCustomFlagsInvalidError,
    ObjectTimestampOrderError,
)
from src.modules.runtime_schema.domain.field.configuration import (
    ArrayDefaultValue,
    ArrayFieldSettings,
    ArrayItemTypeVO,
    DateTimeDefaultValue,
    DateTimeFieldSettings,
    FieldOption,
    MultiSelectDefaultValue,
    MultiSelectFieldOptions,
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
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import (
    ObjectIdVO,
    ObjectNameVO,
)
from src.modules.runtime_schema.domain.source.entity import DataSource
from src.modules.runtime_schema.domain.source.value_object import (
    DataSourceDsnVO,
    DataSourceIdVO,
    DataSourceSchemaVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def _tenant_id() -> EntityIdVO:
    return EntityIdVO.from_value(uuid4())


def _source_id() -> DataSourceIdVO:
    return DataSourceIdVO.from_value(uuid4())


def _object_id() -> ObjectIdVO:
    return ObjectIdVO.from_value(uuid4())


class TestDomainEntities(unittest.TestCase):
    def test_data_source_entity_create_and_set_dsn(self) -> None:
        tenant_id = _tenant_id()
        source = DataSource.create(
            tenant_id=tenant_id,
            source_type="postgresql",
            schema="tenant_schema",
            is_system=True,
            is_remote=False,
        )
        self.assertEqual(source.tenant_id, tenant_id)
        self.assertEqual(source.schema.value, "tenant_schema")
        self.assertIsNone(source.dsn)

        source.set_dsn("postgresql://user:pass@localhost:5432/app")
        self.assertIsNotNone(source.dsn)

    def test_data_source_entity_remote_contract(self) -> None:
        with self.assertRaises(DataSourceRemoteDsnRequiredError):
            DataSource.create(
                tenant_id=_tenant_id(),
                source_type="postgresql",
                schema="tenant_schema",
                is_remote=True,
                dsn=None,
            )

        now = datetime.now(UTC)
        with self.assertRaises(DataSourceTimestampOrderError):
            DataSource(
                id=_source_id(),
                created_at=now,
                updated_at=now - timedelta(seconds=1),
                tenant_id=_tenant_id(),
                type=DataSource.create(
                    tenant_id=_tenant_id(),
                    source_type="postgresql",
                    schema="tenant_schema",
                ).type,
                schema=DataSourceSchemaVO("tenant_schema"),
                is_system=False,
                is_remote=False,
                dsn=None,
            )

    def test_object_metadata_entity_invariants_and_methods(self) -> None:
        entity = ObjectMetadataEntity.create(
            tenant_id=_tenant_id(),
            data_source_id=_source_id(),
            object_name=ObjectNameVO(name_singular="lead", name_plural="leads"),
            is_system=True,
            is_custom=False,
            description="  desc  ",
            icon="  icon  ",
            shortcut="  L  ",
        )
        self.assertEqual(entity.description, "desc")
        self.assertEqual(entity.icon, "icon")
        self.assertEqual(entity.shortcut, "L")
        self.assertTrue(entity.is_active)

        previous_updated_at = entity.updated_at
        entity.rename(
            object_name=ObjectNameVO(name_singular="deal", name_plural="deals"),
        )
        self.assertEqual(entity.object_name.name_singular, "deal")
        self.assertGreaterEqual(entity.updated_at, previous_updated_at)

        entity.deactivate()
        self.assertFalse(entity.is_active)
        entity.activate()
        self.assertTrue(entity.is_active)

        now = datetime.now(UTC)
        with self.assertRaises(ObjectTimestampOrderError):
            ObjectMetadataEntity(
                id=_object_id(),
                created_at=now,
                updated_at=now - timedelta(seconds=1),
                tenant_id=_tenant_id(),
                data_source_id=_source_id(),
                object_name=ObjectNameVO(name_singular="x", name_plural="xs"),
                object_label=ObjectMetadataEntity.create(
                    tenant_id=_tenant_id(),
                    data_source_id=_source_id(),
                    object_name=ObjectNameVO(name_singular="y", name_plural="ys"),
                    is_system=True,
                    is_custom=False,
                ).object_label,
                description=None,
                icon=None,
                shortcut=None,
                is_remote=False,
                is_system=True,
                is_custom=False,
                is_active=True,
                is_ui_read_only=False,
                duplicate_criteria={},
            )

        with self.assertRaises(ObjectSystemCustomFlagsInvalidError):
            ObjectMetadataEntity.create(
                tenant_id=_tenant_id(),
                data_source_id=_source_id(),
                object_name=ObjectNameVO(name_singular="contact", name_plural="contacts"),
                is_system=True,
                is_custom=True,
            )

    def test_field_metadata_entity_create_and_mutations(self) -> None:
        tenant_id = _tenant_id()
        object_id = _object_id()
        options = SelectFieldOptions(
            items=(FieldOption(code="new", label="New"),),
            allow_custom=False,
        )
        entity = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_id,
            field_type=FieldTypeVO.SELECT,
            field_name=FieldName("status"),
            label="  Status  ",
            is_system=True,
            is_custom=False,
            is_index=True,
            options=options,
            default_value=SelectDefaultValue(code="new"),
        )
        self.assertEqual(entity.label, "Status")
        self.assertEqual(entity.field_name.value, "status")

        updated_at = entity.updated_at
        entity.set_default_value(SelectDefaultValue(code="new"))
        self.assertGreaterEqual(entity.updated_at, updated_at)

        previous_options = entity.options
        with self.assertRaises(FieldOptionsRequiredError):
            entity.set_options(None)
        self.assertEqual(entity.options, previous_options)

    def test_field_metadata_entity_contract_errors(self) -> None:
        tenant_id = _tenant_id()
        object_id = _object_id()
        now = datetime.now(UTC)

        with self.assertRaises(FieldTimestampOrderError):
            FieldMetadataEntity(
                id=FieldIdVO.from_value(uuid4()),
                created_at=now,
                updated_at=now - timedelta(seconds=1),
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("title"),
                label="Title",
                description=None,
                icon=None,
                is_system=True,
                is_custom=False,
                is_active=True,
                is_unique=False,
                is_index=False,
                is_nullable=True,
                is_ui_read_only=False,
                is_searchable=False,
                options=None,
                settings=None,
                default_value=None,
                relation_target_object_id=None,
                relation_target_field_id=None,
            )

        with self.assertRaises(FieldSystemCustomFlagsInvalidError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("title"),
                label="Title",
                is_system=True,
                is_custom=True,
            )

        with self.assertRaises(FieldUniqueMustBeIndexedError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("code"),
                label="Code",
                is_system=True,
                is_custom=False,
                is_unique=True,
                is_index=False,
            )

        with self.assertRaises(FieldRelationTargetRequiredError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.RELATION,
                field_name=FieldName("owner"),
                label="Owner",
                is_system=True,
                is_custom=False,
            )

        with self.assertRaises(FieldRelationTargetNotAllowedError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("title"),
                label="Title",
                is_system=True,
                is_custom=False,
                relation_target_object_id=_object_id(),
            )

        with self.assertRaises(FieldOptionsRequiredError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.SELECT,
                field_name=FieldName("status"),
                label="Status",
                is_system=True,
                is_custom=False,
                options=None,
            )

        with self.assertRaises(FieldOptionsNotAllowedError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("title"),
                label="Title",
                is_system=True,
                is_custom=False,
                options=SelectFieldOptions(items=(FieldOption(code="a", label="A"),)),
            )

    def test_field_metadata_default_contracts(self) -> None:
        tenant_id = _tenant_id()
        object_id = _object_id()

        with self.assertRaises(FieldDefaultOptionNotFoundError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.SELECT,
                field_name=FieldName("status"),
                label="Status",
                is_system=True,
                is_custom=False,
                options=SelectFieldOptions(items=(FieldOption(code="new", label="New"),)),
                default_value=SelectDefaultValue(code="archived"),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.DATE_TIME,
                field_name=FieldName("planned_at"),
                label="Planned At",
                is_system=True,
                is_custom=False,
                settings=DateTimeFieldSettings(timezone_aware=True, require_utc=True),
                default_value=DateTimeDefaultValue(
                    value=datetime.now().replace(tzinfo=None)
                ),
            )

        with self.assertRaises(FieldDefaultValueInvalidError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.ARRAY,
                field_name=FieldName("numbers"),
                label="Numbers",
                is_system=True,
                is_custom=False,
                settings=ArrayFieldSettings(item_type=ArrayItemTypeVO.INTEGER),
                default_value=ArrayDefaultValue(values=("x",)),
            )

    def test_field_metadata_multiselect_limits(self) -> None:
        tenant_id = _tenant_id()
        object_id = _object_id()
        with self.assertRaises(FieldDefaultExceedsMaxItemsError):
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_id,
                field_type=FieldTypeVO.MULTI_SELECT,
                field_name=FieldName("tags"),
                label="Tags",
                is_system=True,
                is_custom=False,
                options=MultiSelectFieldOptions(
                    items=(
                        FieldOption(code="a", label="A"),
                        FieldOption(code="b", label="B"),
                    ),
                    max_items=1,
                ),
                default_value=MultiSelectDefaultValue(codes=("a", "b")),
            )

    def test_field_settings_rollback_on_invalid_change(self) -> None:
        tenant_id = _tenant_id()
        object_id = _object_id()
        entity = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_id,
            field_type=FieldTypeVO.STRING,
            field_name=FieldName("title"),
            label="Title",
            is_system=True,
            is_custom=False,
            settings=StringFieldSettings(min_length=1, max_length=20),
            default_value=StringDefaultValue(value="ok"),
        )
        previous_settings = entity.settings
        with self.assertRaises(Exception):
            entity.set_settings(ArrayFieldSettings())
        self.assertEqual(entity.settings, previous_settings)


if __name__ == "__main__":
    unittest.main()
