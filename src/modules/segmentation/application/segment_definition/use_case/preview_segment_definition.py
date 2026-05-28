from typing import Protocol

from src.modules.segmentation.application.segment_definition.query import (
    PreviewSegmentDefinitionQuery,
)
from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
)
from src.modules.segmentation.application.segment_version.dto import SegmentPreviewDTO
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionEvaluationService,
)
from src.modules.segmentation.application.segment_version.use_case.preview_common import (
    build_preview_options,
    build_segment_preview_dto,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionArchivedError,
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
    SegmentKindVO,
    SegmentStatusVO,
)


class PreviewSegmentDefinitionUseCaseProtocol(Protocol):
    """Use case port for previewing segment definition."""

    async def __call__(
        self,
        query: PreviewSegmentDefinitionQuery,
    ) -> SegmentPreviewDTO:
        """Returns read-only segment definition preview."""
        ...


class PreviewSegmentDefinitionUseCase:
    """Previews existing Contact segment definition."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        evaluation_service: SegmentVersionEvaluationService,
        contact_lookup: ContactLookupProtocol,
    ) -> None:
        self._segment_repository = segment_repository
        self._evaluation_service = evaluation_service
        self._contact_lookup = contact_lookup

    async def __call__(
        self,
        query: PreviewSegmentDefinitionQuery,
    ) -> SegmentPreviewDTO:
        options = build_preview_options(
            limit=query.limit,
            offset=query.offset,
        )
        segment = await self._segment_repository.load(
            tenant_id=query.tenant_id,
            segment_id=query.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(query.segment_id.uuid))
        if segment.status == SegmentStatusVO.ARCHIVED:
            raise SegmentDefinitionArchivedError(str(query.segment_id.uuid))

        if segment.segment_kind == SegmentKindVO.STATIC:
            evaluation = await self._evaluation_service.evaluate_static_segment(
                tenant_id=query.tenant_id,
                segment_id=query.segment_id,
                options=options,
            )
        else:
            evaluation = await self._evaluation_service.evaluate_version(
                tenant_id=query.tenant_id,
                segment_id=query.segment_id,
                segment_version_id=query.segment_version_id,
                options=options,
            )
        return await build_segment_preview_dto(
            tenant_id=query.tenant_id,
            evaluation=evaluation,
            limit=query.limit,
            offset=query.offset,
            include_contact_summary=query.include_contact_summary,
            contact_lookup=self._contact_lookup,
        )


__all__ = [
    "PreviewSegmentDefinitionUseCase",
    "PreviewSegmentDefinitionUseCaseProtocol",
]
