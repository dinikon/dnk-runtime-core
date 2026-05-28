from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.modules.segmentation.application.segment_version.dsl.config import (
    SegmentVersionDslConfig,
    SegmentVersionDslRule,
    dump_segment_version_dsl_config,
    parse_segment_version_dsl_config,
)
from src.modules.segmentation.application.segment_version.dsl.error import (
    SegmentVersionDslInvalidContactMappingError,
    SegmentVersionDslInvalidInheritedSegmentError,
    SegmentVersionDslInvalidRelationPathError,
    SegmentVersionDslInvalidRootObjectError,
    SegmentVersionDslInvalidRuleError,
    SegmentVersionDslRuleLimitError,
)
from src.modules.segmentation.application.segment_version.dsl.filter_validator import (
    assert_segment_version_filter_mapping,
)
from src.modules.segmentation.application.segment_version.dsl.relation_path import (
    parse_segment_version_relation_path_item,
)
from src.modules.segmentation.application.segment_version.query.runtime_filter_validator import (
    RuntimeFilterValidatorProtocol,
)
from src.modules.segmentation.application.segment_version.query.runtime_object_metadata import (
    RuntimeObjectMetadataProtocol,
    SegmentVersionRuntimeRelationMetadata,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentIdVO,
    SegmentStatusVO,
)
from src.modules.shared import EntityIdVO

_ROOT_OBJECT = "contact"
_MAX_INCLUDE_RULES = 10
_MAX_EXCLUDE_RULES = 10
_MAX_INHERITED_INCLUDE_SEGMENTS = 10
_MAX_INHERITED_EXCLUDE_SEGMENTS = 10
_MAX_RELATION_DEPTH = 2
_CONTACT_MAPPING_FIELD_TYPES = {"uuid", "reference"}


class SegmentVersionDslConfigValidator:
    """Validates segment version DSL config using runtime metadata only."""

    def __init__(
        self,
        *,
        metadata: RuntimeObjectMetadataProtocol,
        filter_validator: RuntimeFilterValidatorProtocol,
        segment_definition_repository: SegmentDefinitionCommandRepositoryProtocol,
    ) -> None:
        self._metadata = metadata
        self._filter_validator = filter_validator
        self._segment_definition_repository = segment_definition_repository

    async def validate(
        self,
        *,
        tenant_id: EntityIdVO,
        config: Mapping[str, Any] | SegmentVersionDslConfig,
        current_segment_id: SegmentIdVO | None = None,
    ) -> SegmentVersionDslConfig:
        """Validate raw or typed segment version DSL config."""
        parsed = (
            config
            if isinstance(config, SegmentVersionDslConfig)
            else parse_segment_version_dsl_config(config)
        )
        if parsed.root_object != _ROOT_OBJECT:
            raise SegmentVersionDslInvalidRootObjectError(
                "root_object must be contact.",
                path="root_object",
            )

        self._validate_unique_rule_ids(parsed)
        self._validate_limits(parsed)
        await self._validate_inherited_segments(
            tenant_id=tenant_id,
            config=parsed,
            current_segment_id=current_segment_id,
        )
        for index, rule in enumerate(parsed.include):
            await self._validate_rule(
                tenant_id=tenant_id,
                rule=rule,
                path=f"include[{index}]",
            )
        for index, rule in enumerate(parsed.exclude):
            await self._validate_rule(
                tenant_id=tenant_id,
                rule=rule,
                path=f"exclude[{index}]",
            )
        return parsed

    def dump(self, config: SegmentVersionDslConfig) -> dict[str, Any]:
        """Dump validated config into canonical JSON-like representation."""
        return dump_segment_version_dsl_config(config)

    @staticmethod
    def _validate_unique_rule_ids(config: SegmentVersionDslConfig) -> None:
        seen: set[str] = set()
        for group_name, rules in (
            ("include", config.include),
            ("exclude", config.exclude),
        ):
            for index, rule in enumerate(rules):
                if rule.rule_id in seen:
                    raise SegmentVersionDslInvalidRuleError(
                        f"Duplicate rule_id '{rule.rule_id}'.",
                        path=f"{group_name}[{index}].rule_id",
                    )
                seen.add(rule.rule_id)

    @staticmethod
    def _validate_limits(config: SegmentVersionDslConfig) -> None:
        if len(config.include) > _MAX_INCLUDE_RULES:
            raise SegmentVersionDslRuleLimitError(
                f"include rules count must not exceed {_MAX_INCLUDE_RULES}.",
                path="include",
            )
        if len(config.exclude) > _MAX_EXCLUDE_RULES:
            raise SegmentVersionDslRuleLimitError(
                f"exclude rules count must not exceed {_MAX_EXCLUDE_RULES}.",
                path="exclude",
            )
        if len(config.inherit_include_segment_ids) > _MAX_INHERITED_INCLUDE_SEGMENTS:
            raise SegmentVersionDslRuleLimitError(
                "inherit_include_segment_ids count must not exceed "
                f"{_MAX_INHERITED_INCLUDE_SEGMENTS}.",
                path="inherit_include_segment_ids",
            )
        if len(config.inherit_exclude_segment_ids) > _MAX_INHERITED_EXCLUDE_SEGMENTS:
            raise SegmentVersionDslRuleLimitError(
                "inherit_exclude_segment_ids count must not exceed "
                f"{_MAX_INHERITED_EXCLUDE_SEGMENTS}.",
                path="inherit_exclude_segment_ids",
            )

    async def _validate_inherited_segments(
        self,
        *,
        tenant_id: EntityIdVO,
        config: SegmentVersionDslConfig,
        current_segment_id: SegmentIdVO | None,
    ) -> None:
        seen: dict[str, str] = {}
        groups = (
            ("inherit_include_segment_ids", config.inherit_include_segment_ids),
            ("inherit_exclude_segment_ids", config.inherit_exclude_segment_ids),
        )
        for group_name, segment_ids in groups:
            for index, segment_id in enumerate(segment_ids):
                path = f"{group_name}[{index}]"
                key = str(segment_id.uuid)
                if key in seen:
                    raise SegmentVersionDslInvalidInheritedSegmentError(
                        f"Duplicate inherited segment id '{key}'.",
                        path=path,
                    )
                seen[key] = path
                if current_segment_id is not None and segment_id == current_segment_id:
                    raise SegmentVersionDslInvalidInheritedSegmentError(
                        "Segment version config cannot inherit current segment.",
                        path=path,
                    )
                segment = await self._segment_definition_repository.load(
                    tenant_id=tenant_id,
                    segment_id=segment_id,
                )
                if segment is None:
                    raise SegmentVersionDslInvalidInheritedSegmentError(
                        "Inherited segment does not exist.",
                        path=path,
                    )
                if segment.status == SegmentStatusVO.ARCHIVED:
                    raise SegmentVersionDslInvalidInheritedSegmentError(
                        "Inherited segment is archived.",
                        path=path,
                    )

    async def _validate_rule(
        self,
        *,
        tenant_id: EntityIdVO,
        rule: SegmentVersionDslRule,
        path: str,
    ) -> None:
        try:
            await self._metadata.resolve_object(
                tenant_id=tenant_id,
                object_name=rule.object,
            )
        except LookupError as exc:
            raise SegmentVersionDslInvalidRuleError(
                f"Unknown rule object '{rule.object}'.",
                path=f"{path}.object",
            ) from exc

        if rule.object == _ROOT_OBJECT:
            self._validate_contact_rule_mapping(rule=rule, path=path)
        else:
            contact_relation = await self._validate_relation_path(
                tenant_id=tenant_id,
                rule=rule,
                path=path,
            )
            await self._validate_non_contact_mapping(
                tenant_id=tenant_id,
                rule=rule,
                path=path,
                contact_relation=contact_relation,
            )

        assert_segment_version_filter_mapping(rule.filter, path=f"{path}.filter")
        await self._filter_validator.validate_filter(
            tenant_id=tenant_id,
            object_name=rule.object,
            filter_config=rule.filter,
            path=f"{path}.filter",
        )

    @staticmethod
    def _validate_contact_rule_mapping(
        *,
        rule: SegmentVersionDslRule,
        path: str,
    ) -> None:
        if rule.relation_path:
            raise SegmentVersionDslInvalidRelationPathError(
                "Contact rules must use an empty relation_path.",
                path=f"{path}.relation_path",
            )
        if rule.contact_mapping.type != "self" or rule.contact_mapping.field != "id":
            raise SegmentVersionDslInvalidContactMappingError(
                "Contact rules must use self/id contact_mapping.",
                path=f"{path}.contact_mapping",
            )

    async def _validate_relation_path(
        self,
        *,
        tenant_id: EntityIdVO,
        rule: SegmentVersionDslRule,
        path: str,
    ) -> SegmentVersionRuntimeRelationMetadata:
        if not rule.relation_path:
            raise SegmentVersionDslInvalidRelationPathError(
                "Non-contact rules must define relation_path.",
                path=f"{path}.relation_path",
            )
        if len(rule.relation_path) > _MAX_RELATION_DEPTH:
            raise SegmentVersionDslInvalidRelationPathError(
                f"relation_path depth must not exceed {_MAX_RELATION_DEPTH}.",
                path=f"{path}.relation_path",
            )

        current_object = rule.object
        contact_relation: SegmentVersionRuntimeRelationMetadata | None = None
        for index, raw_item in enumerate(rule.relation_path):
            item_path = f"{path}.relation_path[{index}]"
            item = parse_segment_version_relation_path_item(
                raw_item,
                path=item_path,
            )
            if item.source_object != current_object:
                raise SegmentVersionDslInvalidRelationPathError(
                    f"Relation path source must be '{current_object}'.",
                    path=item_path,
                )
            relation = await self._metadata.resolve_relation(
                tenant_id=tenant_id,
                source_object=item.source_object,
                relation_name=item.relation_name,
            )
            if relation is None:
                raise SegmentVersionDslInvalidRelationPathError(
                    "Relation path item does not reference existing relation.",
                    path=item_path,
                )
            current_object = relation.target_object
            if relation.target_object == _ROOT_OBJECT:
                contact_relation = relation

        if current_object != _ROOT_OBJECT or contact_relation is None:
            raise SegmentVersionDslInvalidRelationPathError(
                "Relation path must resolve to contact.",
                path=f"{path}.relation_path",
            )
        return contact_relation

    async def _validate_non_contact_mapping(
        self,
        *,
        tenant_id: EntityIdVO,
        rule: SegmentVersionDslRule,
        path: str,
        contact_relation: SegmentVersionRuntimeRelationMetadata,
    ) -> None:
        if rule.contact_mapping.type != "field":
            raise SegmentVersionDslInvalidContactMappingError(
                "Non-contact rules must use field contact_mapping.",
                path=f"{path}.contact_mapping.type",
            )
        mapping_field = rule.contact_mapping.field
        if (
            contact_relation.fk_field is None
            or contact_relation.fk_field != mapping_field
        ):
            raise SegmentVersionDslInvalidContactMappingError(
                "contact_mapping.field must match relation field to contact.",
                path=f"{path}.contact_mapping.field",
            )
        field_type = await self._metadata.field_type(
            tenant_id=tenant_id,
            object_name=contact_relation.source_object,
            field_name=mapping_field,
        )
        if field_type not in _CONTACT_MAPPING_FIELD_TYPES:
            raise SegmentVersionDslInvalidContactMappingError(
                "contact_mapping.field must be uuid or reference.",
                path=f"{path}.contact_mapping.field",
            )


__all__ = ["SegmentVersionDslConfigValidator"]
