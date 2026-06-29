from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.domain.error import RuntimeDataValidationError
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)


def _contact_descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="contact",
        table_name="contacts",
        pk="id",
        title_field="id",
        fields=(
            RuntimeFieldDescriptor(
                name="id",
                type_code="uuid",
                is_nullable=False,
                default_value="gen_random_uuid()",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="created_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="updated_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="last_name",
                type_code="text",
                is_nullable=True,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="first_name",
                type_code="text",
                is_nullable=False,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="middle_name",
                type_code="text",
                is_nullable=True,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="score",
                type_code="decimal",
                is_nullable=True,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="is_active",
                type_code="bool",
                is_nullable=False,
                default_value="true",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="status",
                type_code="select",
                is_nullable=False,
                default_value="'lead'",
                options={
                    "lead": "Lead",
                    "customer": "Customer",
                    "partner": "Partner",
                },
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="tags",
                type_code="multiselect",
                is_nullable=True,
                default_value=None,
                options={
                    "vip": "VIP",
                    "newsletter": "Newsletter",
                    "inactive": "Inactive",
                },
                settings={},
            ),
        ),
        relations=(),
    )


class RuntimeFieldTypePolicyTests(unittest.TestCase):
    def test_insert_requires_non_nullable_field_without_default(self) -> None:
        policy = RuntimeFieldTypePolicy()
        descriptor = _contact_descriptor()

        with self.assertRaises(RuntimeDataValidationError):
            policy.coerce_insert_payload(
                descriptor=descriptor,
                payload={"id": "d58f4b4d-4bf1-4cca-a3ea-6a99898fbf4c"},
            )

    def test_patch_respects_null_and_immutable_rules(self) -> None:
        policy = RuntimeFieldTypePolicy()
        descriptor = _contact_descriptor()

        with self.assertRaises(RuntimeDataValidationError):
            policy.coerce_patch_payload(
                descriptor=descriptor,
                patch={"updated_at": "2026-01-01T10:00:00+00:00"},
            )

        with self.assertRaises(RuntimeDataValidationError):
            policy.coerce_patch_payload(
                descriptor=descriptor,
                patch={"first_name": None},
            )

        coerced = policy.coerce_patch_payload(
            descriptor=descriptor,
            patch={"last_name": None, "score": "10.25", "is_active": "true"},
        )
        self.assertIsNone(coerced["last_name"])
        self.assertEqual(coerced["score"], Decimal("10.25"))
        self.assertEqual(coerced["is_active"], True)

    def test_patch_rejects_system_fields(self) -> None:
        policy = RuntimeFieldTypePolicy()
        base_descriptor = _contact_descriptor()
        descriptor = RuntimeObjectDescriptor(
            schema_name=base_descriptor.schema_name,
            object_name=base_descriptor.object_name,
            table_name=base_descriptor.table_name,
            pk=base_descriptor.pk,
            title_field=base_descriptor.title_field,
            fields=base_descriptor.fields
            + (
                RuntimeFieldDescriptor(
                    name="workflow_state",
                    type_code="text",
                    is_nullable=True,
                    default_value=None,
                    options={},
                    settings={},
                    kind="system",
                ),
            ),
            relations=base_descriptor.relations,
            kind=base_descriptor.kind,
        )

        with self.assertRaises(RuntimeDataValidationError):
            policy.coerce_patch_payload(
                descriptor=descriptor,
                patch={"workflow_state": "locked"},
            )

    def test_decimal_float_is_rejected(self) -> None:
        policy = RuntimeFieldTypePolicy()
        descriptor = _contact_descriptor()

        with self.assertRaises(RuntimeDataValidationError):
            policy.coerce_patch_payload(
                descriptor=descriptor,
                patch={"score": 1.5},
            )

    def test_datetime_is_normalized_to_utc_aware_on_read(self) -> None:
        policy = RuntimeFieldTypePolicy()
        descriptor = _contact_descriptor()

        normalized = policy.normalize_row(
            descriptor=descriptor,
            row={
                "id": "d58f4b4d-4bf1-4cca-a3ea-6a99898fbf4c",
                "created_at": datetime(2026, 1, 1, 12, 0, 0),
                "updated_at": datetime(2026, 1, 1, 13, 0, 0, tzinfo=UTC),
                "last_name": "Doe",
                "first_name": "Jane",
                "middle_name": None,
                "score": None,
                "is_active": True,
            },
        )

        self.assertIsNotNone(normalized["created_at"].tzinfo)
        self.assertEqual(normalized["updated_at"].tzinfo, UTC)

    def test_datetime_write_value_remains_utc_aware(self) -> None:
        policy = RuntimeFieldTypePolicy()
        descriptor = _contact_descriptor()
        created_at = descriptor.field_by_name("created_at")
        assert created_at is not None

        coerced = policy.coerce_value_for_field(
            field=created_at,
            raw_value="2026-01-01T12:00:00+03:00",
        )

        self.assertEqual(coerced, datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC))
        self.assertEqual(coerced.tzinfo, UTC)

    def test_non_nullable_text_accepts_empty_string(self) -> None:
        policy = RuntimeFieldTypePolicy()
        descriptor = _contact_descriptor()

        coerced = policy.coerce_patch_payload(
            descriptor=descriptor,
            patch={"first_name": ""},
        )

        self.assertEqual(coerced["first_name"], "")

    def test_reference_field_is_coerced_as_uuid(self) -> None:
        policy = RuntimeFieldTypePolicy()
        base_descriptor = _contact_descriptor()
        descriptor = RuntimeObjectDescriptor(
            schema_name=base_descriptor.schema_name,
            object_name=base_descriptor.object_name,
            table_name=base_descriptor.table_name,
            pk=base_descriptor.pk,
            title_field=base_descriptor.title_field,
            fields=base_descriptor.fields
            + (
                RuntimeFieldDescriptor(
                    name="company_id",
                    type_code="reference",
                    is_nullable=True,
                    default_value=None,
                    options={},
                    settings={},
                ),
            ),
            relations=base_descriptor.relations,
            kind=base_descriptor.kind,
        )

        coerced = policy.coerce_patch_payload(
            descriptor=descriptor,
            patch={"company_id": "d58f4b4d-4bf1-4cca-a3ea-6a99898fbf4c"},
        )

        self.assertEqual(
            coerced["company_id"],
            UUID("d58f4b4d-4bf1-4cca-a3ea-6a99898fbf4c"),
        )

    def test_select_and_multiselect_validate_options(self) -> None:
        policy = RuntimeFieldTypePolicy()
        descriptor = _contact_descriptor()

        coerced = policy.coerce_patch_payload(
            descriptor=descriptor,
            patch={
                "status": "customer",
                "tags": ["vip", "newsletter", "vip"],
            },
        )
        self.assertEqual(coerced["status"], "customer")
        self.assertEqual(coerced["tags"], ["vip", "newsletter"])

        with self.assertRaises(RuntimeDataValidationError):
            policy.coerce_patch_payload(
                descriptor=descriptor,
                patch={"status": "unknown"},
            )

        with self.assertRaises(RuntimeDataValidationError):
            policy.coerce_patch_payload(
                descriptor=descriptor,
                patch={"tags": ["vip", "unknown"]},
            )
