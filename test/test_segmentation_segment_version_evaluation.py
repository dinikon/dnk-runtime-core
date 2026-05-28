from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionDslConfig,
    SegmentVersionDslRule,
    dump_segment_version_dsl_config,
    parse_segment_version_dsl_config,
)
from src.modules.segmentation.application.segment_version.dsl.filter_to_runtime import (
    build_runtime_filter_specs,
)
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionActiveVersionNotFoundError,
    SegmentVersionEvaluationDepthExceededError,
    SegmentVersionEvaluationFilterError,
    SegmentVersionEvaluationInheritanceCycleError,
    SegmentVersionEvaluationOptions,
    SegmentVersionEvaluationService,
    SegmentVersionInheritanceEvaluator,
    SegmentVersionRuleExecutor,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentDefinitionArchivedError,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionCommandRepositoryProtocol,
    SegmentVersionIdVO,
    SegmentVersionStatusVO,
)
from src.modules.shared import EntityIdVO


def _field(name: str, type_code: str = "text") -> RuntimeFieldDescriptor:
    return RuntimeFieldDescriptor(
        name=name,
        type_code=type_code,
        is_nullable=False,
        default_value=None,
        options={},
        settings={},
    )


def _descriptor(
    object_name: str,
    fields: tuple[RuntimeFieldDescriptor, ...],
) -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name=object_name,
        table_name=f"{object_name}s",
        pk="id",
        title_field="id",
        fields=fields,
        relations=(),
    )


def _rule(
    rule_id: str,
    *,
    object_name: str = "contact",
    filter_config: dict | None = None,
) -> dict:
    if object_name == "contact":
        return {
            "rule_id": rule_id,
            "object": "contact",
            "relation_path": [],
            "contact_mapping": {"type": "self", "field": "id"},
            "filter": {} if filter_config is None else filter_config,
        }
    return {
        "rule_id": rule_id,
        "object": object_name,
        "relation_path": [f"{object_name}.contact"],
        "contact_mapping": {"type": "field", "field": "contact_id"},
        "filter": {} if filter_config is None else filter_config,
    }


def _config(
    *,
    include: list[dict] | None = None,
    exclude: list[dict] | None = None,
    inherit_include_segment_ids: list[UUID] | None = None,
    inherit_exclude_segment_ids: list[UUID] | None = None,
) -> dict:
    return {
        "root_object": "contact",
        "include": [] if include is None else include,
        "exclude": [] if exclude is None else exclude,
        "inherit_include_segment_ids": [
            str(segment_id) for segment_id in (inherit_include_segment_ids or [])
        ],
        "inherit_exclude_segment_ids": [
            str(segment_id) for segment_id in (inherit_exclude_segment_ids or [])
        ],
    }


def _segment(
    segment_id: SegmentIdVO,
    *,
    kind: SegmentKindVO = SegmentKindVO.DYNAMIC,
    status: SegmentStatusVO = SegmentStatusVO.ACTIVE,
) -> SegmentDefinition:
    return SegmentDefinition(
        segment_id=segment_id,
        name="Segment",
        segment_kind=kind,
        status=status,
    )


def _version(
    segment_id: SegmentIdVO,
    config: dict,
) -> SegmentVersion:
    return SegmentVersion(
        segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
        segment_id=segment_id,
        version_number=1,
        status=SegmentVersionStatusVO.ACTIVE,
        config=config,
        config_checksum="checksum",
    )


class _MetadataStub:
    def __init__(self) -> None:
        self.objects = {
            "contact": _descriptor(
                "contact",
                (
                    _field("id", "uuid"),
                    _field("status", "text"),
                ),
            ),
            "loan_application": _descriptor(
                "loan_application",
                (
                    _field("id", "uuid"),
                    _field("status", "text"),
                    _field("contact_id", "uuid"),
                ),
            ),
        }

    async def resolve_object(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        return self.objects[object_name]


class _ContactAudienceQueryStub:
    def __init__(self, contact_ids: tuple[UUID, ...]) -> None:
        self.contact_ids = contact_ids
        self.calls: list[dict] = []

    async def list_contact_ids(self, **kwargs) -> tuple[UUID, ...]:
        self.calls.append(kwargs)
        return self.contact_ids


class _DslValidatorStub:
    def __init__(self) -> None:
        self.calls: list[SegmentIdVO | None] = []

    async def validate(
        self,
        *,
        tenant_id: EntityIdVO,
        config,
        current_segment_id: SegmentIdVO | None = None,
    ) -> SegmentVersionDslConfig:
        self.calls.append(current_segment_id)
        if isinstance(config, SegmentVersionDslConfig):
            return config
        return parse_segment_version_dsl_config(config)

    def dump(self, config: SegmentVersionDslConfig) -> dict:
        return dump_segment_version_dsl_config(config)


class _RuleExecutorStub:
    def __init__(self, results: dict[str, tuple[UUID, ...]]) -> None:
        self.results = results
        self.calls: list[tuple[str, int | None]] = []

    async def execute_rule(
        self,
        *,
        tenant_id: EntityIdVO,
        rule: SegmentVersionDslRule,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[UUID, ...]:
        self.calls.append((rule.rule_id, limit))
        return self.results.get(rule.rule_id, ())


class _SegmentRepositoryStub:
    def __init__(self, *segments: SegmentDefinition) -> None:
        self.segments = {segment.segment_id: segment for segment in segments}

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinition | None:
        return self.segments.get(segment_id)


class _VersionRepositoryStub(SegmentVersionCommandRepositoryProtocol):
    def __init__(self, *versions: SegmentVersion) -> None:
        self.versions = {version.segment_version_id: version for version in versions}
        self.active_by_segment = {version.segment_id: version for version in versions}

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_version_id: SegmentVersionIdVO,
    ) -> SegmentVersion | None:
        return self.versions.get(segment_version_id)

    async def get_active(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentVersion | None:
        return self.active_by_segment.get(segment_id)

    async def get_next_version_number(self, **kwargs) -> int:
        return 1

    async def save(self, **kwargs) -> SegmentVersion:
        return kwargs["version"]

    async def archive_active_versions(self, **kwargs) -> None:
        return None


class _StaticAudienceQueryStub:
    def __init__(self, results: dict[SegmentIdVO, tuple[UUID, ...]]) -> None:
        self.results = results
        self.calls: list[tuple[SegmentIdVO, int | None]] = []

    async def list_contact_ids(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[UUID, ...]:
        self.calls.append((segment_id, limit))
        return self.results.get(segment_id, ())


class SegmentVersionEvaluationTests(unittest.IsolatedAsyncioTestCase):
    def test_filter_conversion_accepts_empty_simple_and_group_filters(self) -> None:
        descriptor = _descriptor(
            "contact",
            (_field("id", "uuid"), _field("status", "text")),
        )

        self.assertEqual(
            build_runtime_filter_specs(descriptor=descriptor, filter_config={}),
            (),
        )
        simple = build_runtime_filter_specs(
            descriptor=descriptor,
            filter_config={"field": "status", "op": "eq", "value": "active"},
        )
        group = build_runtime_filter_specs(
            descriptor=descriptor,
            filter_config={
                "and": [
                    {"field": "status", "op": "eq", "value": "active"},
                ]
            },
        )

        self.assertEqual(len(simple), 1)
        self.assertEqual(len(group), 1)

    async def test_rule_executor_builds_typed_filters_and_wraps_filter_errors(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = uuid4()
        query = _ContactAudienceQueryStub((contact_id,))
        executor = SegmentVersionRuleExecutor(
            metadata=_MetadataStub(),
            contact_audience_query=query,
        )

        result = await executor.execute_rule(
            tenant_id=tenant_id,
            rule=parse_segment_version_dsl_config(
                _config(
                    include=[
                        _rule(
                            "active",
                            filter_config={
                                "field": "status",
                                "op": "eq",
                                "value": "active",
                            },
                        )
                    ]
                )
            ).include[0],
        )

        self.assertEqual(result, (contact_id,))
        self.assertEqual(query.calls[0]["object_name"], "contact")
        self.assertEqual(len(query.calls[0]["filters"]), 1)

        with self.assertRaises(SegmentVersionEvaluationFilterError):
            await executor.execute_rule(
                tenant_id=tenant_id,
                rule=parse_segment_version_dsl_config(
                    _config(
                        include=[
                            _rule(
                                "bad",
                                filter_config={
                                    "field": "missing",
                                    "op": "eq",
                                    "value": "active",
                                },
                            )
                        ]
                    )
                ).include[0],
            )

    async def test_service_dedupes_excludes_and_paginates_after_evaluation(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_a = uuid4()
        contact_b = uuid4()
        contact_c = uuid4()
        service = self._service(
            rule_executor=_RuleExecutorStub(
                {
                    "include-a": (contact_a, contact_b, contact_a),
                    "include-b": (contact_c,),
                    "exclude": (contact_b,),
                }
            )
        )

        result = await service.evaluate_config(
            tenant_id=tenant_id,
            config=_config(
                include=[_rule("include-a"), _rule("include-b")],
                exclude=[_rule("exclude")],
            ),
            options=SegmentVersionEvaluationOptions(limit=1, offset=1),
        )

        self.assertEqual(result.contact_ids, (contact_c,))
        self.assertEqual(result.count, 1)

    async def test_service_evaluates_static_segment_with_final_pagination(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_a = uuid4()
        contact_b = uuid4()
        static_query = _StaticAudienceQueryStub(
            {
                segment_id: (contact_a, contact_b),
            }
        )
        service = self._service(static_query=static_query)

        result = await service.evaluate_static_segment(
            tenant_id=tenant_id,
            segment_id=segment_id,
            options=SegmentVersionEvaluationOptions(limit=1, offset=1, max_items=100),
        )

        self.assertEqual(result.contact_ids, (contact_b,))
        self.assertEqual(static_query.calls[0], (segment_id, 100))

    async def test_service_rejects_archived_segment_version_preview(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version = _version(segment_id, _config())
        service = self._service(
            segment_repository=_SegmentRepositoryStub(
                _segment(
                    segment_id,
                    status=SegmentStatusVO.ARCHIVED,
                )
            ),
            version_repository=_VersionRepositoryStub(version),
        )

        with self.assertRaises(SegmentDefinitionArchivedError):
            await service.evaluate_version(
                tenant_id=tenant_id,
                segment_id=segment_id,
                segment_version_id=version.segment_version_id,
            )

    async def test_service_evaluates_static_and_dynamic_inherited_segments(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        root_segment_id = SegmentIdVO.from_value(uuid4())
        static_segment_id = SegmentIdVO.from_value(uuid4())
        dynamic_segment_id = SegmentIdVO.from_value(uuid4())
        static_contact_id = uuid4()
        dynamic_contact_id = uuid4()
        dynamic_version = _version(
            dynamic_segment_id,
            _config(include=[_rule("dynamic-include")]),
        )
        service = self._service(
            segment_repository=_SegmentRepositoryStub(
                _segment(root_segment_id),
                _segment(static_segment_id, kind=SegmentKindVO.STATIC),
                _segment(dynamic_segment_id),
            ),
            version_repository=_VersionRepositoryStub(dynamic_version),
            static_query=_StaticAudienceQueryStub(
                {
                    static_segment_id: (static_contact_id,),
                }
            ),
            rule_executor=_RuleExecutorStub(
                {
                    "dynamic-include": (dynamic_contact_id,),
                }
            ),
        )

        result = await service.evaluate_config(
            tenant_id=tenant_id,
            current_segment_id=root_segment_id,
            config=_config(
                inherit_include_segment_ids=[
                    static_segment_id.uuid,
                    dynamic_segment_id.uuid,
                ],
            ),
        )

        self.assertEqual(result.contact_ids, (static_contact_id, dynamic_contact_id))

    async def test_service_detects_inheritance_cycle_and_missing_active_version(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        root_segment_id = SegmentIdVO.from_value(uuid4())
        child_segment_id = SegmentIdVO.from_value(uuid4())
        child_version = _version(
            child_segment_id,
            _config(inherit_include_segment_ids=[root_segment_id.uuid]),
        )
        service = self._service(
            segment_repository=_SegmentRepositoryStub(
                _segment(root_segment_id),
                _segment(child_segment_id),
            ),
            version_repository=_VersionRepositoryStub(child_version),
        )

        with self.assertRaises(SegmentVersionEvaluationInheritanceCycleError):
            await service.evaluate_config(
                tenant_id=tenant_id,
                current_segment_id=root_segment_id,
                config=_config(inherit_include_segment_ids=[child_segment_id.uuid]),
            )

        missing_active_service = self._service(
            segment_repository=_SegmentRepositoryStub(_segment(child_segment_id)),
            version_repository=_VersionRepositoryStub(),
        )
        with self.assertRaises(SegmentVersionActiveVersionNotFoundError):
            await missing_active_service.evaluate_config(
                tenant_id=tenant_id,
                config=_config(inherit_include_segment_ids=[child_segment_id.uuid]),
            )

    async def test_inheritance_evaluator_enforces_max_depth(self) -> None:
        evaluator = SegmentVersionInheritanceEvaluator(
            segment_repository=_SegmentRepositoryStub(),
            version_repository=_VersionRepositoryStub(),
            static_audience_query=_StaticAudienceQueryStub({}),
        )

        with self.assertRaises(SegmentVersionEvaluationDepthExceededError):
            await evaluator.evaluate_inherited_segments(
                tenant_id=EntityIdVO.from_value(uuid4()),
                segment_ids=(),
                options=SegmentVersionEvaluationOptions(),
                visited_segment_ids=frozenset(),
                depth=3,
                evaluate_dynamic_segment=lambda *args: None,
            )

    @staticmethod
    def _service(
        *,
        segment_repository: _SegmentRepositoryStub | None = None,
        version_repository: _VersionRepositoryStub | None = None,
        static_query: _StaticAudienceQueryStub | None = None,
        rule_executor: _RuleExecutorStub | None = None,
    ) -> SegmentVersionEvaluationService:
        segment_repo = segment_repository or _SegmentRepositoryStub()
        version_repo = version_repository or _VersionRepositoryStub()
        static_audience_query = static_query or _StaticAudienceQueryStub({})
        return SegmentVersionEvaluationService(
            dsl_validator=_DslValidatorStub(),
            rule_executor=rule_executor or _RuleExecutorStub({}),
            inheritance_evaluator=SegmentVersionInheritanceEvaluator(
                segment_repository=segment_repo,
                version_repository=version_repo,
                static_audience_query=static_audience_query,
            ),
            segment_repository=segment_repo,
            version_repository=version_repo,
            static_audience_query=static_audience_query,
        )


__all__ = ["SegmentVersionEvaluationTests"]
