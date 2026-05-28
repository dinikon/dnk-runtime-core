from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.segmentation.application.segment_definition import (
    PreviewSegmentDefinitionQuery,
    PreviewSegmentDefinitionUseCase,
)
from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)
from src.modules.segmentation.application.segment_version import (
    PreviewSegmentConfigCommand,
    PreviewSegmentConfigUseCase,
    PreviewSegmentVersionQuery,
    PreviewSegmentVersionUseCase,
    SegmentVersionEvaluationResult,
)
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionDslInvalidRootObjectError,
    parse_segment_version_dsl_config,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO
from src.modules.shared import EntityIdVO


def _contact_config() -> dict:
    return {
        "root_object": "contact",
        "include": [],
        "exclude": [],
        "inherit_include_segment_ids": [],
        "inherit_exclude_segment_ids": [],
    }


def _segment(
    segment_id: SegmentIdVO,
    *,
    kind: SegmentKindVO,
    status: SegmentStatusVO = SegmentStatusVO.ACTIVE,
) -> SegmentDefinition:
    return SegmentDefinition(
        segment_id=segment_id,
        name="VIP",
        segment_kind=kind,
        status=status,
    )


class _DslValidatorStub:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.calls = []

    async def validate(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return parse_segment_version_dsl_config(kwargs["config"])


class _EvaluationServiceStub:
    def __init__(self, contact_ids=()) -> None:
        self.result = SegmentVersionEvaluationResult(
            contact_ids=tuple(contact_ids),
            count=len(tuple(contact_ids)),
        )
        self.config_calls = []
        self.version_calls = []
        self.static_calls = []

    async def evaluate_config(self, **kwargs):
        self.config_calls.append(kwargs)
        return self.result

    async def evaluate_version(self, **kwargs):
        self.version_calls.append(kwargs)
        return self.result

    async def evaluate_static_segment(self, **kwargs):
        self.static_calls.append(kwargs)
        return self.result


class _ContactLookupStub:
    def __init__(self, summaries=None) -> None:
        self.summaries = summaries or {}
        self.calls = []

    async def get_summaries(self, **kwargs):
        self.calls.append(kwargs)
        return self.summaries


class _SegmentRepositoryStub:
    def __init__(self, segment: SegmentDefinition | None = None) -> None:
        self.segment = segment
        self.loads = []

    async def load(self, **kwargs):
        self.loads.append(kwargs)
        return self.segment


class SegmentationPreviewUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_raw_config_preview_returns_contact_ids_and_ordered_summaries(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_a = uuid4()
        contact_b = uuid4()
        lookup = _ContactLookupStub(
            {
                contact_b: ContactSummaryDTO(
                    id=contact_b,
                    first_name="B",
                    last_name=None,
                    middle_name=None,
                    status="active",
                ),
                contact_a: ContactSummaryDTO(
                    id=contact_a,
                    first_name="A",
                    last_name=None,
                    middle_name=None,
                    status="active",
                ),
            }
        )
        evaluation = _EvaluationServiceStub((contact_a, contact_b))
        use_case = PreviewSegmentConfigUseCase(
            dsl_validator=_DslValidatorStub(),
            evaluation_service=evaluation,
            contact_lookup=lookup,
        )

        result = await use_case(
            PreviewSegmentConfigCommand(
                tenant_id=tenant_id,
                config=_contact_config(),
                limit=2,
                offset=0,
                include_contact_summary=True,
            )
        )

        self.assertEqual(result.contact_ids, (contact_a, contact_b))
        self.assertEqual(
            [contact.first_name for contact in result.contacts], ["A", "B"]
        )
        self.assertEqual(lookup.calls[0]["contact_ids"][0].uuid, contact_a)
        self.assertTrue(result.has_more)
        self.assertEqual(evaluation.config_calls[0]["options"].limit, 2)

    async def test_raw_invalid_dsl_error_is_not_swallowed(self) -> None:
        use_case = PreviewSegmentConfigUseCase(
            dsl_validator=_DslValidatorStub(
                SegmentVersionDslInvalidRootObjectError(
                    "root_object must be contact.",
                    path="root_object",
                )
            ),
            evaluation_service=_EvaluationServiceStub(),
            contact_lookup=_ContactLookupStub(),
        )

        with self.assertRaises(SegmentVersionDslInvalidRootObjectError):
            await use_case(
                PreviewSegmentConfigCommand(
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    config={"root_object": "company"},
                )
            )

    async def test_preview_keeps_contact_ids_when_summary_is_missing(self) -> None:
        contact_a = uuid4()
        contact_b = uuid4()
        use_case = PreviewSegmentConfigUseCase(
            dsl_validator=_DslValidatorStub(),
            evaluation_service=_EvaluationServiceStub((contact_a, contact_b)),
            contact_lookup=_ContactLookupStub(
                {
                    contact_b: ContactSummaryDTO(
                        id=contact_b,
                        first_name="B",
                        last_name=None,
                        middle_name=None,
                        status=None,
                    )
                }
            ),
        )

        result = await use_case(
            PreviewSegmentConfigCommand(
                tenant_id=EntityIdVO.from_value(uuid4()),
                config=_contact_config(),
                limit=50,
                offset=0,
            )
        )

        self.assertEqual(result.contact_ids, (contact_a, contact_b))
        self.assertEqual([contact.id for contact in result.contacts], [contact_b])

    async def test_preview_without_summaries_does_not_call_contact_lookup(self) -> None:
        lookup = _ContactLookupStub()
        use_case = PreviewSegmentConfigUseCase(
            dsl_validator=_DslValidatorStub(),
            evaluation_service=_EvaluationServiceStub((uuid4(),)),
            contact_lookup=lookup,
        )

        result = await use_case(
            PreviewSegmentConfigCommand(
                tenant_id=EntityIdVO.from_value(uuid4()),
                config=_contact_config(),
                include_contact_summary=False,
            )
        )

        self.assertEqual(result.contacts, ())
        self.assertEqual(lookup.calls, [])

    async def test_existing_static_segment_preview_uses_static_evaluation(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        evaluation = _EvaluationServiceStub((uuid4(),))
        use_case = PreviewSegmentDefinitionUseCase(
            segment_repository=_SegmentRepositoryStub(
                _segment(segment_id, kind=SegmentKindVO.STATIC)
            ),
            evaluation_service=evaluation,
            contact_lookup=_ContactLookupStub(),
        )

        result = await use_case(
            PreviewSegmentDefinitionQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
                include_contact_summary=False,
            )
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(evaluation.version_calls, [])
        self.assertEqual(evaluation.static_calls[0]["segment_id"], segment_id)

    async def test_existing_dynamic_segment_preview_uses_active_or_requested_version(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        evaluation = _EvaluationServiceStub((uuid4(),))
        use_case = PreviewSegmentDefinitionUseCase(
            segment_repository=_SegmentRepositoryStub(
                _segment(segment_id, kind=SegmentKindVO.DYNAMIC)
            ),
            evaluation_service=evaluation,
            contact_lookup=_ContactLookupStub(),
        )

        await use_case(
            PreviewSegmentDefinitionQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                include_contact_summary=False,
            )
        )
        await use_case(
            PreviewSegmentDefinitionQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                segment_version_id=version_id,
                include_contact_summary=False,
            )
        )

        self.assertIsNone(evaluation.version_calls[0]["segment_version_id"])
        self.assertEqual(evaluation.version_calls[1]["segment_version_id"], version_id)

    async def test_version_preview_uses_exact_version_id(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        evaluation = _EvaluationServiceStub((uuid4(),))
        use_case = PreviewSegmentVersionUseCase(
            evaluation_service=evaluation,
            contact_lookup=_ContactLookupStub(),
        )

        await use_case(
            PreviewSegmentVersionQuery(
                tenant_id=tenant_id,
                segment_id=segment_id,
                segment_version_id=version_id,
                limit=25,
                include_contact_summary=False,
            )
        )

        self.assertEqual(evaluation.version_calls[0]["segment_id"], segment_id)
        self.assertEqual(evaluation.version_calls[0]["segment_version_id"], version_id)
        self.assertEqual(evaluation.version_calls[0]["options"].limit, 25)


__all__ = ["SegmentationPreviewUseCaseTests"]
