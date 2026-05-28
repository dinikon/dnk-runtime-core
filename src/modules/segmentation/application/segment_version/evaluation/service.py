from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from src.modules.segmentation.application.segment_static_member.query import (
    StaticContactAudienceQueryProtocol,
)
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionDslConfig,
    SegmentVersionDslConfigValidator,
)
from src.modules.segmentation.application.segment_version.evaluation.inheritance import (
    SegmentVersionInheritanceEvaluator,
)
from src.modules.segmentation.application.segment_version.evaluation.model import (
    SegmentVersionEvaluationOptions,
    SegmentVersionEvaluationResult,
)
from src.modules.segmentation.application.segment_version.evaluation.rule_executor import (
    SegmentVersionRuleExecutor,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
    SegmentKindVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionCommandRepositoryProtocol,
    SegmentVersionIdVO,
    SegmentVersionNotFoundError,
)
from src.modules.segmentation.application.segment_version.evaluation.error import (
    SegmentVersionActiveVersionNotFoundError,
)
from src.modules.shared import EntityIdVO


class SegmentVersionEvaluationService:
    """Evaluates Contact audience for segment version DSL config."""

    def __init__(
        self,
        *,
        dsl_validator: SegmentVersionDslConfigValidator,
        rule_executor: SegmentVersionRuleExecutor,
        inheritance_evaluator: SegmentVersionInheritanceEvaluator,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        version_repository: SegmentVersionCommandRepositoryProtocol,
        static_audience_query: StaticContactAudienceQueryProtocol,
    ) -> None:
        self._dsl_validator = dsl_validator
        self._rule_executor = rule_executor
        self._inheritance_evaluator = inheritance_evaluator
        self._segment_repository = segment_repository
        self._version_repository = version_repository
        self._static_audience_query = static_audience_query

    async def evaluate_config(
        self,
        *,
        tenant_id: EntityIdVO,
        config: Mapping[str, Any] | SegmentVersionDslConfig,
        options: SegmentVersionEvaluationOptions | None = None,
        current_segment_id: SegmentIdVO | None = None,
    ) -> SegmentVersionEvaluationResult:
        evaluation_options = options or SegmentVersionEvaluationOptions()
        dsl_config = await self._dsl_validator.validate(
            tenant_id=tenant_id,
            config=config,
            current_segment_id=current_segment_id,
        )
        contact_ids = await self._evaluate_validated_config(
            tenant_id=tenant_id,
            config=dsl_config,
            options=evaluation_options,
            visited_segment_ids=self._initial_visited(current_segment_id),
            depth=0,
        )
        return self._build_result(
            contact_ids=contact_ids,
            options=evaluation_options,
        )

    async def evaluate_version(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        segment_version_id: SegmentVersionIdVO | None = None,
        options: SegmentVersionEvaluationOptions | None = None,
    ) -> SegmentVersionEvaluationResult:
        segment = await self._segment_repository.load(
            tenant_id=tenant_id,
            segment_id=segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(segment_id.uuid))
        if segment.segment_kind == SegmentKindVO.STATIC and segment_version_id is None:
            return await self.evaluate_static_segment(
                tenant_id=tenant_id,
                segment_id=segment_id,
                options=options,
            )

        if segment_version_id is None:
            version = await self._version_repository.get_active(
                tenant_id=tenant_id,
                segment_id=segment_id,
            )
            if version is None:
                raise SegmentVersionActiveVersionNotFoundError(str(segment_id.uuid))
        else:
            version = await self._version_repository.load(
                tenant_id=tenant_id,
                segment_version_id=segment_version_id,
            )
            if version is None or version.segment_id != segment_id:
                raise SegmentVersionNotFoundError(str(segment_version_id.uuid))

        return await self.evaluate_config(
            tenant_id=tenant_id,
            config=version.config,
            options=options,
            current_segment_id=segment_id,
        )

    async def evaluate_static_segment(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        options: SegmentVersionEvaluationOptions | None = None,
    ) -> SegmentVersionEvaluationResult:
        evaluation_options = options or SegmentVersionEvaluationOptions()
        contact_ids = await self._static_audience_query.list_contact_ids(
            tenant_id=tenant_id,
            segment_id=segment_id,
            limit=evaluation_options.max_items,
            offset=0,
        )
        return self._build_result(
            contact_ids=contact_ids,
            options=evaluation_options,
        )

    async def _evaluate_validated_config(
        self,
        *,
        tenant_id: EntityIdVO,
        config: SegmentVersionDslConfig,
        options: SegmentVersionEvaluationOptions,
        visited_segment_ids: frozenset[UUID],
        depth: int,
    ) -> tuple[UUID, ...]:
        include_ids: list[UUID] = []
        exclude_ids: list[UUID] = []

        for rule in config.include:
            include_ids.extend(
                await self._rule_executor.execute_rule(
                    tenant_id=tenant_id,
                    rule=rule,
                    limit=options.max_items,
                    offset=0,
                )
            )

        include_ids.extend(
            await self._inheritance_evaluator.evaluate_inherited_segments(
                tenant_id=tenant_id,
                segment_ids=config.inherit_include_segment_ids,
                options=options,
                visited_segment_ids=visited_segment_ids,
                depth=depth,
                evaluate_dynamic_segment=self._dynamic_segment_callback(
                    tenant_id=tenant_id,
                    options=options,
                ),
            )
        )

        for rule in config.exclude:
            exclude_ids.extend(
                await self._rule_executor.execute_rule(
                    tenant_id=tenant_id,
                    rule=rule,
                    limit=options.max_items,
                    offset=0,
                )
            )

        exclude_ids.extend(
            await self._inheritance_evaluator.evaluate_inherited_segments(
                tenant_id=tenant_id,
                segment_ids=config.inherit_exclude_segment_ids,
                options=options,
                visited_segment_ids=visited_segment_ids,
                depth=depth,
                evaluate_dynamic_segment=self._dynamic_segment_callback(
                    tenant_id=tenant_id,
                    options=options,
                ),
            )
        )

        excluded = set(exclude_ids)
        return tuple(
            contact_id
            for contact_id in self._dedupe_preserving_order(include_ids)
            if contact_id not in excluded
        )

    def _dynamic_segment_callback(
        self,
        *,
        tenant_id: EntityIdVO,
        options: SegmentVersionEvaluationOptions,
    ):
        async def evaluate_dynamic_segment(
            segment_id: SegmentIdVO,
            version: SegmentVersion,
            visited_segment_ids: frozenset[UUID],
            depth: int,
        ) -> tuple[UUID, ...]:
            dsl_config = await self._dsl_validator.validate(
                tenant_id=tenant_id,
                config=version.config,
                current_segment_id=segment_id,
            )
            return await self._evaluate_validated_config(
                tenant_id=tenant_id,
                config=dsl_config,
                options=options,
                visited_segment_ids=visited_segment_ids,
                depth=depth,
            )

        return evaluate_dynamic_segment

    @staticmethod
    def _initial_visited(
        current_segment_id: SegmentIdVO | None,
    ) -> frozenset[UUID]:
        if current_segment_id is None:
            return frozenset()
        return frozenset({current_segment_id.uuid})

    @staticmethod
    def _build_result(
        *,
        contact_ids: tuple[UUID, ...],
        options: SegmentVersionEvaluationOptions,
    ) -> SegmentVersionEvaluationResult:
        sliced = contact_ids[options.offset :]
        if options.limit is not None:
            sliced = sliced[: options.limit]
        return SegmentVersionEvaluationResult(
            contact_ids=tuple(sliced),
            count=len(sliced),
        )

    @staticmethod
    def _dedupe_preserving_order(contact_ids: list[UUID]) -> tuple[UUID, ...]:
        seen: set[UUID] = set()
        result: list[UUID] = []
        for contact_id in contact_ids:
            if contact_id in seen:
                continue
            seen.add(contact_id)
            result.append(contact_id)
        return tuple(result)


__all__ = ["SegmentVersionEvaluationService"]
