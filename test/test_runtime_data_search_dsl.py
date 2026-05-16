from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from src.modules.runtime_data import RuntimeDataFilterError
from src.modules.runtime_data.application.query.filter_dsl import (
    FilterDslParser,
    FilterSemanticValidator,
)
from src.modules.runtime_data.application.query.sort_dsl import (
    SortDslParser,
    SortSemanticValidator,
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
                name="id",
                type_code="uuid",
                is_nullable=False,
                default_value="gen_random_uuid()",
                options={},
                settings={},
                kind="system",
            ),
            RuntimeFieldDescriptor(
                name="created_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                options={},
                settings={},
                kind="system",
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
                name="status",
                type_code="select",
                is_nullable=False,
                default_value="'lead'",
                options={"lead": "Lead", "partner": "Partner"},
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
                name="tags",
                type_code="multiselect",
                is_nullable=True,
                default_value=None,
                options={"vip": "VIP", "newsletter": "Newsletter"},
                settings={},
                is_filterable=True,
                is_sortable=False,
            ),
            RuntimeFieldDescriptor(
                name="internal_hash",
                type_code="text",
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


class RuntimeDataFilterDslTests(unittest.TestCase):
    def test_parser_accepts_nested_groups_and_conditions(self) -> None:
        parsed = FilterDslParser().parse(
            {
                "and": [
                    {"field": "status", "op": "eq", "value": "lead"},
                    {
                        "or": [
                            {"field": "first_name", "op": "contains", "value": "den"},
                            {"field": "score", "op": "gte", "value": "10.5"},
                        ]
                    },
                ]
            }
        )

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].logic, "and")

    def test_parser_rejects_unknown_keys(self) -> None:
        with self.assertRaisesRegex(
            RuntimeDataFilterError, "INVALID_FILTER_DSL"
        ) as caught:
            FilterDslParser().parse(
                {"field": "status", "operator": "eq", "value": "lead"}
            )
        self.assertEqual(caught.exception.code, "INVALID_FILTER_DSL")

    def test_parser_enforces_depth_and_condition_limits(self) -> None:
        too_deep = {
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
        with self.assertRaisesRegex(RuntimeDataFilterError, "depth") as caught:
            FilterDslParser(max_depth=5).parse(too_deep)
        self.assertEqual(caught.exception.code, "INVALID_FILTER_DSL")

        with self.assertRaisesRegex(
            RuntimeDataFilterError, "condition count"
        ) as caught:
            FilterDslParser(max_conditions=2).parse(
                {
                    "and": [
                        {"field": "status", "op": "eq", "value": "lead"},
                        {"field": "status", "op": "eq", "value": "partner"},
                        {"field": "first_name", "op": "contains", "value": "den"},
                    ]
                }
            )
        self.assertEqual(caught.exception.code, "INVALID_FILTER_DSL")

    def test_semantic_validator_coerces_valid_values(self) -> None:
        ast = FilterDslParser().parse(
            {
                "and": [
                    {"field": "first_name", "op": "contains", "value": "den"},
                    {"field": "first_name", "op": "starts_with", "value": "de"},
                    {"field": "first_name", "op": "ends_with", "value": "is"},
                    {"field": "status", "op": "eq", "value": "lead"},
                    {"field": "status", "op": "in", "value": ["lead", "partner"]},
                    {
                        "field": "tags",
                        "op": "contains_any",
                        "value": ["vip", "newsletter"],
                    },
                    {"field": "score", "op": "between", "value": ["1.5", "2.5"]},
                    {
                        "field": "created_at",
                        "op": "gte",
                        "value": "2026-01-01T00:00:00",
                    },
                    {"field": "id", "op": "eq", "value": str(uuid4())},
                ]
            }
        )

        filters = FilterSemanticValidator().validate(
            descriptor=_descriptor(),
            filter_ast=ast,
        )

        group = filters[0]
        self.assertEqual(group.logic, "and")
        self.assertEqual(group.items[1].op, "starts_with")
        self.assertEqual(group.items[2].op, "ends_with")
        self.assertEqual(group.items[3].value, "lead")
        self.assertEqual(group.items[4].value, ["lead", "partner"])
        self.assertEqual(group.items[5].value, ["vip", "newsletter"])
        self.assertIsInstance(group.items[6].value[0], Decimal)
        self.assertIsInstance(group.items[7].value, datetime)

    def test_multiselect_contains_any_validates(self) -> None:
        filters = FilterSemanticValidator().validate(
            descriptor=_descriptor(),
            filter_ast=FilterDslParser().parse(
                {
                    "field": "tags",
                    "op": "contains_any",
                    "value": ["vip"],
                }
            ),
        )

        self.assertEqual(filters[0].field, "tags")
        self.assertEqual(filters[0].op, "contains_any")
        self.assertEqual(filters[0].value, ["vip"])

    def test_multiselect_contains_all_validates(self) -> None:
        filters = FilterSemanticValidator().validate(
            descriptor=_descriptor(),
            filter_ast=FilterDslParser().parse(
                {
                    "field": "tags",
                    "op": "contains_all",
                    "value": ["vip", "newsletter"],
                }
            ),
        )

        self.assertEqual(filters[0].field, "tags")
        self.assertEqual(filters[0].op, "contains_all")
        self.assertEqual(filters[0].value, ["vip", "newsletter"])

    def test_multiselect_not_contains_any_validates(self) -> None:
        filters = FilterSemanticValidator().validate(
            descriptor=_descriptor(),
            filter_ast=FilterDslParser().parse(
                {
                    "field": "tags",
                    "op": "not_contains_any",
                    "value": ["vip"],
                }
            ),
        )

        self.assertEqual(filters[0].field, "tags")
        self.assertEqual(filters[0].op, "not_contains_any")
        self.assertEqual(filters[0].value, ["vip"])

    def test_multiselect_rejects_scalar_value(self) -> None:
        with self.assertRaisesRegex(
            RuntimeDataFilterError,
            "INVALID_FILTER_VALUE_TYPE",
        ) as caught:
            FilterSemanticValidator().validate(
                descriptor=_descriptor(),
                filter_ast=FilterDslParser().parse(
                    {
                        "field": "tags",
                        "op": "contains_any",
                        "value": "vip",
                    }
                ),
            )

        self.assertEqual(caught.exception.code, "INVALID_FILTER_VALUE_TYPE")
        self.assertEqual(caught.exception.details["field"], "tags")
        self.assertEqual(caught.exception.details["operator"], "contains_any")

    def test_multiselect_rejects_unknown_option(self) -> None:
        with self.assertRaisesRegex(
            RuntimeDataFilterError,
            "INVALID_FIELD_OPTION",
        ) as caught:
            FilterSemanticValidator().validate(
                descriptor=_descriptor(),
                filter_ast=FilterDslParser().parse(
                    {
                        "field": "tags",
                        "op": "contains_any",
                        "value": ["unknown"],
                    }
                ),
            )

        self.assertEqual(caught.exception.code, "INVALID_FIELD_OPTION")
        self.assertEqual(caught.exception.details["field"], "tags")
        self.assertEqual(caught.exception.details["value"], "unknown")

    def test_multiselect_is_empty_ignores_value(self) -> None:
        filters = FilterSemanticValidator().validate(
            descriptor=_descriptor(),
            filter_ast=FilterDslParser().parse(
                {
                    "field": "tags",
                    "op": "is_empty",
                    "value": ["vip"],
                }
            ),
        )

        self.assertEqual(filters[0].field, "tags")
        self.assertEqual(filters[0].op, "is_empty")
        self.assertIsNone(filters[0].value)

    def test_multiselect_is_not_empty_ignores_value(self) -> None:
        filters = FilterSemanticValidator().validate(
            descriptor=_descriptor(),
            filter_ast=FilterDslParser().parse(
                {
                    "field": "tags",
                    "op": "is_not_empty",
                    "value": ["vip"],
                }
            ),
        )

        self.assertEqual(filters[0].field, "tags")
        self.assertEqual(filters[0].op, "is_not_empty")
        self.assertIsNone(filters[0].value)

    def test_filter_rejects_not_filterable_field(self) -> None:
        with self.assertRaisesRegex(
            RuntimeDataFilterError,
            "FIELD_IS_NOT_FILTERABLE",
        ) as caught:
            FilterSemanticValidator().validate(
                descriptor=_descriptor(),
                filter_ast=FilterDslParser().parse(
                    {
                        "field": "internal_hash",
                        "op": "eq",
                        "value": "abc",
                    }
                ),
            )

        self.assertEqual(caught.exception.code, "FIELD_IS_NOT_FILTERABLE")
        self.assertEqual(caught.exception.details["field"], "internal_hash")

    def test_system_field_filterability_comes_from_descriptor(self) -> None:
        descriptor = RuntimeObjectDescriptor(
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
                    kind="system",
                    is_filterable=False,
                    is_sortable=True,
                ),
                RuntimeFieldDescriptor(
                    name="internal_hash",
                    type_code="text",
                    is_nullable=True,
                    default_value=None,
                    options={},
                    settings={},
                    kind="system",
                    is_filterable=True,
                    is_sortable=False,
                ),
            ),
            relations=(),
        )

        filters = FilterSemanticValidator().validate(
            descriptor=descriptor,
            filter_ast=FilterDslParser().parse(
                {
                    "field": "internal_hash",
                    "op": "eq",
                    "value": "abc",
                }
            ),
        )
        self.assertEqual(filters[0].field, "internal_hash")

        with self.assertRaisesRegex(
            RuntimeDataFilterError,
            "FIELD_IS_NOT_FILTERABLE",
        ) as caught:
            FilterSemanticValidator().validate(
                descriptor=descriptor,
                filter_ast=FilterDslParser().parse(
                    {
                        "field": "id",
                        "op": "eq",
                        "value": str(uuid4()),
                    }
                ),
            )
        self.assertEqual(caught.exception.code, "FIELD_IS_NOT_FILTERABLE")
        self.assertEqual(caught.exception.details["field"], "id")

    def test_semantic_validator_rejects_unknown_field_operator_and_value(self) -> None:
        descriptor = _descriptor()
        validator = FilterSemanticValidator()

        for payload, expected_code in (
            (
                {"field": "unknown", "op": "eq", "value": "lead"},
                "UNKNOWN_FILTER_FIELD",
            ),
            (
                {"field": "status", "op": "contains", "value": "lead"},
                "UNSUPPORTED_OPERATOR_FOR_FIELD_TYPE",
            ),
            (
                {"field": "tags", "op": "contains", "value": "vip"},
                "UNSUPPORTED_OPERATOR_FOR_FIELD_TYPE",
            ),
            (
                {"field": "status", "op": "eq", "value": "archived"},
                "INVALID_FIELD_OPTION",
            ),
            (
                {"field": "created_at", "op": "gte", "value": "not-a-date"},
                "INVALID_FILTER_VALUE_TYPE",
            ),
        ):
            with self.subTest(expected_code=expected_code):
                with self.assertRaisesRegex(
                    RuntimeDataFilterError,
                    expected_code,
                ) as caught:
                    validator.validate(
                        descriptor=descriptor,
                        filter_ast=FilterDslParser().parse(payload),
                    )
                self.assertEqual(caught.exception.code, expected_code)
                if payload["field"] == "status" and expected_code == (
                    "UNSUPPORTED_OPERATOR_FOR_FIELD_TYPE"
                ):
                    self.assertEqual(caught.exception.details["field"], "status")
                    self.assertEqual(caught.exception.details["field_type"], "select")
                    self.assertEqual(caught.exception.details["operator"], "contains")
                if payload["field"] == "tags":
                    self.assertEqual(caught.exception.details["field"], "tags")
                    self.assertEqual(
                        caught.exception.details["field_type"],
                        "multiselect",
                    )
                    self.assertEqual(caught.exception.details["operator"], "contains")


class RuntimeDataSortDslTests(unittest.TestCase):
    def test_sort_parser_and_validator_accept_valid_sort(self) -> None:
        ast = SortDslParser().parse([{"field": "created_at", "direction": "DESC"}])
        sorting = SortSemanticValidator().validate(
            descriptor=_descriptor(),
            sort_ast=ast,
        )

        self.assertEqual(sorting[0].field, "created_at")
        self.assertEqual(sorting[0].direction, "desc")

    def test_sort_rejects_invalid_direction_unknown_field_and_multiselect(self) -> None:
        with self.assertRaisesRegex(
            RuntimeDataFilterError, "INVALID_SORT_DSL"
        ) as caught:
            SortDslParser().parse([{"field": "created_at", "direction": "sideways"}])
        self.assertEqual(caught.exception.code, "INVALID_SORT_DSL")

        for payload, expected_code in (
            ([{"field": "unknown", "direction": "asc"}], "UNKNOWN_SORT_FIELD"),
            ([{"field": "tags", "direction": "asc"}], "FIELD_IS_NOT_SORTABLE"),
        ):
            with self.subTest(expected_code=expected_code):
                with self.assertRaisesRegex(
                    RuntimeDataFilterError,
                    expected_code,
                ) as caught:
                    SortSemanticValidator().validate(
                        descriptor=_descriptor(),
                        sort_ast=SortDslParser().parse(payload),
                    )
                self.assertEqual(caught.exception.code, expected_code)

    def test_sort_rejects_not_sortable_field(self) -> None:
        with self.assertRaisesRegex(
            RuntimeDataFilterError,
            "FIELD_IS_NOT_SORTABLE",
        ) as caught:
            SortSemanticValidator().validate(
                descriptor=_descriptor(),
                sort_ast=SortDslParser().parse(
                    [{"field": "internal_hash", "direction": "asc"}]
                ),
            )

        self.assertEqual(caught.exception.code, "FIELD_IS_NOT_SORTABLE")
        self.assertEqual(caught.exception.details["field"], "internal_hash")

    def test_multiselect_is_filterable_but_not_sortable(self) -> None:
        filters = FilterSemanticValidator().validate(
            descriptor=_descriptor(),
            filter_ast=FilterDslParser().parse(
                {
                    "field": "tags",
                    "op": "contains_any",
                    "value": ["vip"],
                }
            ),
        )
        self.assertEqual(filters[0].field, "tags")

        with self.assertRaisesRegex(
            RuntimeDataFilterError,
            "FIELD_IS_NOT_SORTABLE",
        ) as caught:
            SortSemanticValidator().validate(
                descriptor=_descriptor(),
                sort_ast=SortDslParser().parse([{"field": "tags", "direction": "asc"}]),
            )

        self.assertEqual(caught.exception.code, "FIELD_IS_NOT_SORTABLE")
        self.assertEqual(caught.exception.details["field"], "tags")


__all__ = ["RuntimeDataFilterDslTests", "RuntimeDataSortDslTests"]
