from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.modules.runtime_data.application.query.filter_dsl.ast import (
    FilterConditionNode,
    FilterGroupNode,
    FilterNode,
)
from src.modules.runtime_data.application.query.filter_dsl.errors import (
    filter_dsl_error,
)


class FilterDslParser:
    """Parses public JSON filter DSL into a small syntax AST."""

    def __init__(
        self,
        *,
        max_depth: int = 5,
        max_conditions: int = 50,
    ) -> None:
        self._max_depth = max_depth
        self._max_conditions = max_conditions

    def parse(self, payload: Any) -> tuple[FilterNode, ...]:
        """Parse raw public filter payload into syntax nodes."""

        if payload is None or payload == {}:
            return ()
        counter = _ConditionCounter()
        node = self._parse_node(payload=payload, depth=1, counter=counter)
        return (node,)

    def _parse_node(
        self,
        *,
        payload: Any,
        depth: int,
        counter: "_ConditionCounter",
    ) -> FilterNode:
        if depth > self._max_depth:
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                f"Filter nesting depth must not exceed {self._max_depth}.",
            )

        if not isinstance(payload, Mapping):
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                "Filter expression must be an object.",
            )

        has_and = "and" in payload
        has_or = "or" in payload
        if has_and or has_or:
            return self._parse_group(payload=payload, depth=depth, counter=counter)
        return self._parse_condition(payload=payload, counter=counter)

    def _parse_group(
        self,
        *,
        payload: Mapping[Any, Any],
        depth: int,
        counter: "_ConditionCounter",
    ) -> FilterGroupNode:
        has_and = "and" in payload
        has_or = "or" in payload
        if has_and and has_or:
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                "Filter group must contain only one of 'and' or 'or'.",
            )
        if set(payload.keys()) != {"and"} and set(payload.keys()) != {"or"}:
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                "Filter group cannot contain keys other than 'and' or 'or'.",
            )

        logic = "and" if has_and else "or"
        raw_items = payload[logic]
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                f"Filter group '{logic}' requires a list of expressions.",
            )
        if not raw_items:
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                f"Filter group '{logic}' requires at least one expression.",
            )

        return FilterGroupNode(
            logic=logic,
            items=tuple(
                self._parse_node(payload=item, depth=depth + 1, counter=counter)
                for item in raw_items
            ),
        )

    def _parse_condition(
        self,
        *,
        payload: Mapping[Any, Any],
        counter: "_ConditionCounter",
    ) -> FilterConditionNode:
        if set(payload.keys()) != {"field", "op", "value"}:
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                "Filter condition must contain only field, op and value.",
            )

        field_name = payload["field"]
        operator = payload["op"]
        if not isinstance(field_name, str) or not field_name.strip():
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                "Filter condition field must be a non-empty string.",
            )
        if not isinstance(operator, str) or not operator.strip():
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                "Filter condition op must be a non-empty string.",
            )

        counter.increment(max_conditions=self._max_conditions)
        return FilterConditionNode(
            field=field_name.strip(),
            operator=operator.strip().lower(),
            value=payload["value"],
        )


class _ConditionCounter:
    def __init__(self) -> None:
        self.value = 0

    def increment(self, *, max_conditions: int) -> None:
        self.value += 1
        if self.value > max_conditions:
            raise filter_dsl_error(
                "INVALID_FILTER_DSL",
                f"Filter condition count must not exceed {max_conditions}.",
            )


__all__ = ["FilterDslParser"]
