from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.domain import RuntimeDataValidationError
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
                is_system=True,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="created_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                is_system=True,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="updated_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                is_system=True,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="last_name",
                type_code="text",
                is_nullable=False,
                default_value=None,
                is_system=False,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="first_name",
                type_code="text",
                is_nullable=True,
                default_value=None,
                is_system=False,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="middle_name",
                type_code="text",
                is_nullable=True,
                default_value=None,
                is_system=False,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="score",
                type_code="decimal",
                is_nullable=True,
                default_value=None,
                is_system=False,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="is_active",
                type_code="bool",
                is_nullable=False,
                default_value="true",
                is_system=False,
                options={},
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
                patch={"last_name": None},
            )

        coerced = policy.coerce_patch_payload(
            descriptor=descriptor,
            patch={"first_name": None, "score": "10.25", "is_active": "true"},
        )
        self.assertIsNone(coerced["first_name"])
        self.assertEqual(coerced["score"], Decimal("10.25"))
        self.assertEqual(coerced["is_active"], True)

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
                "first_name": None,
                "middle_name": None,
                "score": None,
                "is_active": True,
            },
        )

        self.assertIsNotNone(normalized["created_at"].tzinfo)
        self.assertEqual(normalized["updated_at"].tzinfo, UTC)
