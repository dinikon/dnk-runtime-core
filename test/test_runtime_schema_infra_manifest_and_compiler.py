from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from src.modules.runtime_schema.domain.field.configuration import DateTimeDefaultValue
from src.modules.runtime_schema.domain.field.value_object import FieldTypeVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.metadata_compiler import MetadataCompiler
from src.modules.runtime_schema.infrastructure.system_manifest_reader import (
    YamlSystemModelRegistryReader,
)
from src.modules.shared.domain.errors import ValidationError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class TestManifestReaderAndCompiler(unittest.IsolatedAsyncioTestCase):
    async def test_reader_loads_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.yaml"
            path.write_text(
                """
version: "1.0.0"
module: "crm"
objects:
  - key: "lead"
    name:
      singular: "lead"
      plural: "leads"
    label:
      singular: "Lead"
      plural: "Leads"
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
      - name: "status"
        type: "select"
        label: "Status"
        options:
          items:
            - code: "new"
              label: "New"
          allow_custom: false
        default_value:
          code: "new"
""".strip(),
                encoding="utf-8",
            )
            reader = YamlSystemModelRegistryReader(path)
            manifest = await reader.load_system_manifest()
            self.assertEqual(manifest.version, "1.0.0")
            self.assertEqual(manifest.module, "crm")
            self.assertEqual(len(manifest.objects), 1)
            self.assertEqual(manifest.objects[0].key, "lead")

    async def test_reader_supports_datetime_now_default_shorthand(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.yaml"
            path.write_text(
                """
version: "1.0.0"
module: "crm"
objects:
  - key: "contact"
    name: {singular: "contact", plural: "contacts"}
    label: {singular: "Contact", plural: "Contacts"}
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
      - name: "created_at"
        type: "date_time"
        label: "Created At"
        is_nullable: false
        default_value: "now"
      - name: "updated_at"
        type: "date_time"
        label: "Updated At"
        is_nullable: false
        default_values: "now"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            fields = manifest.objects[0].fields
            created_at_field = next(field for field in fields if field.name == "created_at")
            updated_at_field = next(field for field in fields if field.name == "updated_at")
            self.assertEqual(created_at_field.default_value, {"value": "now"})
            self.assertEqual(updated_at_field.default_value, {"value": "now"})

    async def test_reader_validation_errors(self) -> None:
        with TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.yaml"
            reader = YamlSystemModelRegistryReader(missing_path)
            with self.assertRaises(ValidationError):
                await reader.load_system_manifest()

            invalid_path = Path(tmpdir) / "invalid.yaml"
            invalid_path.write_text("[]", encoding="utf-8")
            reader = YamlSystemModelRegistryReader(invalid_path)
            with self.assertRaises(ValidationError):
                await reader.load_system_manifest()

            invalid_path.write_text("version: ''\nobjects: []", encoding="utf-8")
            with self.assertRaises(ValidationError):
                await reader.load_system_manifest()

    async def test_reader_duplicate_object_and_field_names(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.yaml"
            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    fields: []
  - key: "lead"
    name: {singular: "lead_copy", plural: "lead_copies"}
    label: {singular: "Lead Copy", plural: "Lead Copies"}
    fields: []
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError):
                await YamlSystemModelRegistryReader(path).load_system_manifest()

            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "company"
    name: {singular: "company", plural: "companies"}
    label: {singular: "Company", plural: "Companies"}
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
      - name: "ID"
        type: "uuid"
        label: "ID copy"
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError):
                await YamlSystemModelRegistryReader(path).load_system_manifest()

    async def test_compiler_builds_metadata_and_relations(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.yaml"
            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
      - name: "company_id"
        type: "relation"
        label: "Company"
        relation_target_object: "company"
        relation_target_field: "id"
        settings:
          max_links: 1
  - key: "company"
    name: {singular: "company", plural: "companies"}
    label: {singular: "Company", plural: "Companies"}
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            compiler = MetadataCompiler()
            bundle = compiler.compile_system_schema(
                manifest=manifest,
                tenant_id=EntityIdVO.from_value(uuid4()),
                data_source_id=DataSourceIdVO.from_value(uuid4()),
            )
            self.assertEqual(len(bundle.objects), 2)
            self.assertEqual(len(bundle.fields), 3)
            lead_fields = bundle.fields_by_object_key["lead"]
            relation = next(item for item in lead_fields if item.field_name.value == "company_id")
            self.assertEqual(relation.field_type, FieldTypeVO.RELATION)
            self.assertIsNotNone(relation.relation_target_object_id)
            self.assertIsNotNone(relation.relation_target_field_id)

    async def test_compiler_supports_datetime_now_default(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.yaml"
            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "note"
    name: {singular: "note", plural: "notes"}
    label: {singular: "Note", plural: "Notes"}
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
      - name: "created_at"
        type: "date_time"
        label: "Created At"
        is_nullable: false
        default_value: "now"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            compiler = MetadataCompiler()
            before_compile = datetime.now(UTC)
            bundle = compiler.compile_system_schema(
                manifest=manifest,
                tenant_id=EntityIdVO.from_value(uuid4()),
                data_source_id=DataSourceIdVO.from_value(uuid4()),
            )
            after_compile = datetime.now(UTC)

            note_fields = bundle.fields_by_object_key["note"]
            created_at_field = next(
                field for field in note_fields if field.field_name.value == "created_at"
            )
            self.assertIsInstance(created_at_field.default_value, DateTimeDefaultValue)
            assert isinstance(created_at_field.default_value, DateTimeDefaultValue)
            self.assertGreaterEqual(created_at_field.default_value.value, before_compile)
            self.assertLessEqual(created_at_field.default_value.value, after_compile)

    async def test_compiler_validation_errors(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.yaml"
            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    fields:
      - name: "bad"
        type: "unknown"
        label: "Bad"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            compiler = MetadataCompiler()
            with self.assertRaises(ValidationError):
                compiler.compile_system_schema(
                    manifest=manifest,
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    data_source_id=DataSourceIdVO.from_value(uuid4()),
                )

            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    fields:
      - name: "owner_id"
        type: "relation"
        label: "Owner"
        relation_target_object: "missing_object"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            with self.assertRaises(ValidationError):
                compiler.compile_system_schema(
                    manifest=manifest,
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    data_source_id=DataSourceIdVO.from_value(uuid4()),
                )

            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    fields:
      - name: "status"
        type: "select"
        label: "Status"
        options:
          items: "not-list"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            with self.assertRaises(ValidationError):
                compiler.compile_system_schema(
                    manifest=manifest,
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    data_source_id=DataSourceIdVO.from_value(uuid4()),
                )

            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    fields:
      - name: "name"
        type: "string"
        label: "Name"
        relation_target_field: "id"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            with self.assertRaises(ValidationError):
                compiler.compile_system_schema(
                    manifest=manifest,
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    data_source_id=DataSourceIdVO.from_value(uuid4()),
                )

            path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    fields:
      - name: "company_id"
        type: "relation"
        label: "Company"
        relation_target_object: "company"
        relation_target_field: "code"
  - key: "company"
    name: {singular: "company", plural: "companies"}
    label: {singular: "Company", plural: "Companies"}
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
""".strip(),
                encoding="utf-8",
            )
            manifest = await YamlSystemModelRegistryReader(path).load_system_manifest()
            with self.assertRaises(ValidationError):
                compiler.compile_system_schema(
                    manifest=manifest,
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    data_source_id=DataSourceIdVO.from_value(uuid4()),
                )


if __name__ == "__main__":
    unittest.main()
