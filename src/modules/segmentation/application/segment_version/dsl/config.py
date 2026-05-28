from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from src.modules.segmentation.application.segment_version.dsl.error import (
    SegmentVersionDslInvalidContactMappingError,
    SegmentVersionDslInvalidInheritedSegmentError,
    SegmentVersionDslInvalidRootObjectError,
    SegmentVersionDslInvalidRuleError,
    SegmentVersionDslParseError,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared.domain.errors import EntityIdTypeError

_TOP_LEVEL_KEYS = {
    "root_object",
    "include",
    "exclude",
    "inherit_include_segment_ids",
    "inherit_exclude_segment_ids",
}
_RULE_KEYS = {"rule_id", "object", "relation_path", "contact_mapping", "filter"}
_CONTACT_MAPPING_KEYS = {"type", "field"}


@dataclass(slots=True, frozen=True)
class SegmentVersionDslConfig:
    root_object: str
    include: tuple["SegmentVersionDslRule", ...]
    exclude: tuple["SegmentVersionDslRule", ...]
    inherit_include_segment_ids: tuple[SegmentIdVO, ...]
    inherit_exclude_segment_ids: tuple[SegmentIdVO, ...]


@dataclass(slots=True, frozen=True)
class SegmentVersionDslRule:
    rule_id: str
    object: str
    relation_path: tuple[str, ...]
    contact_mapping: "SegmentVersionContactMapping"
    filter: Mapping[str, Any]


@dataclass(slots=True, frozen=True)
class SegmentVersionContactMapping:
    type: Literal["self", "field"]
    field: str


def parse_segment_version_dsl_config(
    raw: Mapping[str, Any],
) -> SegmentVersionDslConfig:
    """Parse raw JSON-like config into a typed segment version DSL config."""
    payload = _expect_mapping(raw, path="")
    extra_keys = set(payload.keys()) - _TOP_LEVEL_KEYS
    if extra_keys:
        formatted_keys = ", ".join(sorted(str(key) for key in extra_keys))
        raise SegmentVersionDslParseError(
            f"Unknown top-level keys: {formatted_keys}.",
            path="root",
        )

    if "root_object" not in payload:
        raise SegmentVersionDslInvalidRootObjectError(
            "root_object is required.",
            path="root_object",
        )
    root_object = _expect_string(payload["root_object"], path="root_object")
    if root_object != "contact":
        raise SegmentVersionDslInvalidRootObjectError(
            "root_object must be contact.",
            path="root_object",
        )

    include = _parse_rules(payload.get("include", ()), path="include")
    exclude = _parse_rules(payload.get("exclude", ()), path="exclude")
    _ensure_unique_rule_ids(include=include, exclude=exclude)

    return SegmentVersionDslConfig(
        root_object=root_object,
        include=include,
        exclude=exclude,
        inherit_include_segment_ids=_parse_segment_ids(
            payload.get("inherit_include_segment_ids", ()),
            path="inherit_include_segment_ids",
        ),
        inherit_exclude_segment_ids=_parse_segment_ids(
            payload.get("inherit_exclude_segment_ids", ()),
            path="inherit_exclude_segment_ids",
        ),
    )


def dump_segment_version_dsl_config(
    config: SegmentVersionDslConfig,
) -> dict[str, Any]:
    """Dump a typed segment version DSL config into canonical JSON-like dict."""
    return {
        "root_object": config.root_object,
        "include": [_dump_rule(rule) for rule in config.include],
        "exclude": [_dump_rule(rule) for rule in config.exclude],
        "inherit_include_segment_ids": [
            str(segment_id.uuid) for segment_id in config.inherit_include_segment_ids
        ],
        "inherit_exclude_segment_ids": [
            str(segment_id.uuid) for segment_id in config.inherit_exclude_segment_ids
        ],
    }


def _parse_rules(raw: Any, *, path: str) -> tuple[SegmentVersionDslRule, ...]:
    items = _expect_sequence(raw, path=path)
    return tuple(
        _parse_rule(item, path=f"{path}[{index}]") for index, item in enumerate(items)
    )


def _parse_rule(raw: Any, *, path: str) -> SegmentVersionDslRule:
    payload = _expect_mapping(raw, path=path)
    keys = set(payload.keys())
    if keys != _RULE_KEYS:
        missing = sorted(_RULE_KEYS - keys)
        extra = sorted(str(key) for key in keys - _RULE_KEYS)
        detail_parts = []
        if missing:
            detail_parts.append(f"missing: {', '.join(missing)}")
        if extra:
            detail_parts.append(f"unknown: {', '.join(extra)}")
        raise SegmentVersionDslInvalidRuleError(
            "Rule must contain exactly rule_id, object, relation_path, "
            f"contact_mapping and filter ({'; '.join(detail_parts)}).",
            path=path,
        )

    rule_id = _expect_string(payload["rule_id"], path=f"{path}.rule_id")
    object_name = _expect_string(payload["object"], path=f"{path}.object")
    relation_path = tuple(
        _expect_string(item, path=f"{path}.relation_path[{index}]")
        for index, item in enumerate(
            _expect_sequence(payload["relation_path"], path=f"{path}.relation_path")
        )
    )
    filter_config = _expect_mapping(payload["filter"], path=f"{path}.filter")

    return SegmentVersionDslRule(
        rule_id=rule_id,
        object=object_name,
        relation_path=relation_path,
        contact_mapping=_parse_contact_mapping(
            payload["contact_mapping"],
            path=f"{path}.contact_mapping",
        ),
        filter=deepcopy(dict(filter_config)),
    )


def _parse_contact_mapping(raw: Any, *, path: str) -> SegmentVersionContactMapping:
    payload = _expect_mapping(raw, path=path)
    keys = set(payload.keys())
    if keys != _CONTACT_MAPPING_KEYS:
        raise SegmentVersionDslInvalidContactMappingError(
            "contact_mapping must contain exactly type and field.",
            path=path,
        )
    mapping_type = _expect_string(payload["type"], path=f"{path}.type")
    if mapping_type not in {"self", "field"}:
        raise SegmentVersionDslInvalidContactMappingError(
            "contact_mapping.type must be self or field.",
            path=f"{path}.type",
        )
    return SegmentVersionContactMapping(
        type=mapping_type,
        field=_expect_string(payload["field"], path=f"{path}.field"),
    )


def _parse_segment_ids(raw: Any, *, path: str) -> tuple[SegmentIdVO, ...]:
    items = _expect_sequence(raw, path=path)
    segment_ids: list[SegmentIdVO] = []
    for index, item in enumerate(items):
        try:
            segment_ids.append(SegmentIdVO.from_value(item))
        except (EntityIdTypeError, TypeError, ValueError) as exc:
            raise SegmentVersionDslInvalidInheritedSegmentError(
                "Inherited segment id must be a UUID.",
                path=f"{path}[{index}]",
            ) from exc
    return tuple(segment_ids)


def _ensure_unique_rule_ids(
    *,
    include: tuple[SegmentVersionDslRule, ...],
    exclude: tuple[SegmentVersionDslRule, ...],
) -> None:
    seen: dict[str, str] = {}
    for group_name, rules in (("include", include), ("exclude", exclude)):
        for index, rule in enumerate(rules):
            if rule.rule_id in seen:
                raise SegmentVersionDslInvalidRuleError(
                    f"Duplicate rule_id '{rule.rule_id}'.",
                    path=f"{group_name}[{index}].rule_id",
                )
            seen[rule.rule_id] = f"{group_name}[{index}].rule_id"


def _dump_rule(rule: SegmentVersionDslRule) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "object": rule.object,
        "relation_path": list(rule.relation_path),
        "contact_mapping": {
            "type": rule.contact_mapping.type,
            "field": rule.contact_mapping.field,
        },
        "filter": deepcopy(dict(rule.filter)),
    }


def _expect_mapping(raw: Any, *, path: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        raise SegmentVersionDslParseError(
            "Expected object.",
            path=path or "root",
        )
    return raw


def _expect_sequence(raw: Any, *, path: str) -> Sequence[Any]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise SegmentVersionDslParseError(
            "Expected array.",
            path=path,
        )
    return raw


def _expect_string(raw: Any, *, path: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise SegmentVersionDslParseError(
            "Expected non-empty string.",
            path=path,
        )
    return raw.strip()


__all__ = [
    "SegmentVersionContactMapping",
    "SegmentVersionDslConfig",
    "SegmentVersionDslRule",
    "dump_segment_version_dsl_config",
    "parse_segment_version_dsl_config",
]
