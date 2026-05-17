from __future__ import annotations

import unittest

from src.modules.runtime_data.application.query.capabilities.query_capability_resolver import (
    QueryCapabilityResolver,
)
from src.modules.runtime_data.application.query.filter_dsl.operator_registry import (
    FilterOperatorRegistry,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)


def _descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="contact",
        table_name="contacts",
        pk="id",
        title_field="id",
        fields=(
            RuntimeFieldDescriptor(
                name="status",
                type_code="select",
                is_nullable=False,
                default_value=None,
                options={"lead": "Lead", "customer": "Customer"},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="tags",
                type_code="multiselect",
                is_nullable=True,
                default_value=None,
                options={"vip": "VIP", "inactive": "Inactive"},
                settings={},
                is_filterable=True,
                is_sortable=False,
            ),
            RuntimeFieldDescriptor(
                name="created_at",
                type_code="datetime",
                is_nullable=False,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="payload",
                type_code="json",
                is_nullable=True,
                default_value=None,
                options={},
                settings={},
                is_filterable=False,
                is_sortable=False,
            ),
        ),
        relations=(),
    )


class RuntimeDataQueryCapabilityTests(unittest.TestCase):
    def test_resolves_select_filter_capability_from_operator_registry(self) -> None:
        resolver = QueryCapabilityResolver()

        capabilities = {
            capability.field_name: capability
            for capability in resolver.resolve_for_descriptor(_descriptor())
        }

        status = capabilities["status"]
        self.assertTrue(status.filter.enabled)
        self.assertEqual(status.filter.input, "select")
        self.assertEqual(status.filter.value_type, "string")
        self.assertEqual(
            status.filter.operators,
            FilterOperatorRegistry().operators_for("select"),
        )
        self.assertEqual(
            list(status.filter.options),
            [
                {"value": "lead", "label": "Lead"},
                {"value": "customer", "label": "Customer"},
            ],
        )
        self.assertTrue(status.sort.enabled)

    def test_resolves_multiselect_as_filterable_but_not_sortable(self) -> None:
        capabilities = {
            capability.field_name: capability
            for capability in QueryCapabilityResolver().resolve_for_descriptor(
                _descriptor()
            )
        }

        tags = capabilities["tags"]
        self.assertTrue(tags.filter.enabled)
        self.assertEqual(tags.filter.input, "multiselect")
        self.assertEqual(tags.filter.value_type, "string[]")
        self.assertEqual(
            tags.filter.operators,
            (
                "contains_any",
                "contains_all",
                "not_contains_any",
                "is_empty",
                "is_not_empty",
                "is_null",
                "is_not_null",
            ),
        )
        self.assertEqual(
            list(tags.filter.options),
            [
                {"value": "vip", "label": "VIP"},
                {"value": "inactive", "label": "Inactive"},
            ],
        )
        self.assertFalse(tags.sort.enabled)

    def test_resolves_datetime_filter_capability(self) -> None:
        capabilities = {
            capability.field_name: capability
            for capability in QueryCapabilityResolver().resolve_for_descriptor(
                _descriptor()
            )
        }

        created_at = capabilities["created_at"]
        self.assertTrue(created_at.filter.enabled)
        self.assertEqual(created_at.filter.input, "datetime")
        self.assertEqual(created_at.filter.value_type, "datetime")
        self.assertEqual(
            created_at.filter.operators,
            FilterOperatorRegistry().operators_for("datetime"),
        )
        self.assertTrue(created_at.sort.enabled)

    def test_disables_filter_and_sort_from_descriptor_policy(self) -> None:
        capabilities = {
            capability.field_name: capability
            for capability in QueryCapabilityResolver().resolve_for_descriptor(
                _descriptor()
            )
        }

        payload = capabilities["payload"]
        self.assertFalse(payload.filter.enabled)
        self.assertEqual(payload.filter.operators, ())
        self.assertEqual(payload.filter.input, "json")
        self.assertEqual(payload.filter.value_type, "json")
        self.assertFalse(payload.sort.enabled)


__all__ = ["RuntimeDataQueryCapabilityTests"]
