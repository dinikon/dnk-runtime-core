from __future__ import annotations

import unittest

from src.modules.runtime_data import RuntimeDataFilterError
from src.modules.runtime_data.application.query.filter_dsl import (
    FilterConditionNode,
    FilterDslParser,
    FilterGroupNode,
)


class FilterDslParserPublicContractTests(unittest.TestCase):
    def test_parse_single_condition(self) -> None:
        parsed = FilterDslParser().parse(
            {"field": "last_name", "op": "is_null", "value": None}
        )

        self.assertEqual(
            parsed,
            (
                FilterConditionNode(
                    field="last_name",
                    operator="is_null",
                    value=None,
                ),
            ),
        )

    def test_parse_and_group(self) -> None:
        parsed = FilterDslParser().parse(
            {
                "and": [
                    {"field": "status", "op": "eq", "value": "lead"},
                    {
                        "field": "created_at",
                        "op": "gte",
                        "value": "2026-01-01T00:00:00",
                    },
                ]
            }
        )

        group = parsed[0]
        self.assertIsInstance(group, FilterGroupNode)
        self.assertEqual(group.logic, "and")
        self.assertEqual(len(group.items), 2)
        self.assertEqual(group.items[0].field, "status")
        self.assertEqual(group.items[1].operator, "gte")

    def test_parse_nested_or_group(self) -> None:
        parsed = FilterDslParser().parse(
            {
                "and": [
                    {"field": "status", "op": "in", "value": ["lead", "customer"]},
                    {
                        "or": [
                            {
                                "field": "first_name",
                                "op": "contains",
                                "value": "den",
                            },
                            {
                                "field": "last_name",
                                "op": "contains",
                                "value": "nik",
                            },
                        ]
                    },
                ]
            }
        )

        root = parsed[0]
        nested = root.items[1]
        self.assertEqual(root.logic, "and")
        self.assertIsInstance(nested, FilterGroupNode)
        self.assertEqual(nested.logic, "or")
        self.assertEqual(nested.items[0].field, "first_name")
        self.assertEqual(nested.items[1].value, "nik")

    def test_parse_rejects_unknown_condition_keys(self) -> None:
        with self.assertRaisesRegex(RuntimeDataFilterError, "INVALID_FILTER_DSL"):
            FilterDslParser().parse(
                {"field": "status", "op": "eq", "value": "lead", "extra": True}
            )

    def test_parse_rejects_group_with_and_and_or_together(self) -> None:
        with self.assertRaisesRegex(RuntimeDataFilterError, "INVALID_FILTER_DSL"):
            FilterDslParser().parse({"and": [], "or": []})

    def test_parse_rejects_empty_group(self) -> None:
        with self.assertRaisesRegex(RuntimeDataFilterError, "INVALID_FILTER_DSL"):
            FilterDslParser().parse({"and": []})

    def test_parse_rejects_too_deep_filter(self) -> None:
        payload = {
            "and": [
                {
                    "and": [
                        {
                            "and": [
                                {
                                    "and": [
                                        {
                                            "and": [
                                                {
                                                    "field": "status",
                                                    "op": "eq",
                                                    "value": "lead",
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        with self.assertRaisesRegex(RuntimeDataFilterError, "depth"):
            FilterDslParser(max_depth=5).parse(payload)

    def test_parse_rejects_too_many_conditions(self) -> None:
        with self.assertRaisesRegex(RuntimeDataFilterError, "condition count"):
            FilterDslParser(max_conditions=2).parse(
                {
                    "and": [
                        {"field": "status", "op": "eq", "value": "lead"},
                        {"field": "status", "op": "eq", "value": "customer"},
                        {"field": "first_name", "op": "contains", "value": "den"},
                    ]
                }
            )

    def test_parse_requires_value_even_for_is_null(self) -> None:
        with self.assertRaisesRegex(RuntimeDataFilterError, "INVALID_FILTER_DSL"):
            FilterDslParser().parse({"field": "last_name", "op": "is_null"})


__all__ = ["FilterDslParserPublicContractTests"]
