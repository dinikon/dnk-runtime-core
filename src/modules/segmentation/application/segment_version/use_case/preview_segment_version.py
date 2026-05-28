from typing import Protocol

from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
)
from src.modules.segmentation.application.segment_version.dto import SegmentPreviewDTO
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionEvaluationService,
)
from src.modules.segmentation.application.segment_version.query import (
    PreviewSegmentVersionQuery,
)
from src.modules.segmentation.application.segment_version.use_case.preview_common import (
    build_preview_options,
    build_segment_preview_dto,
)


class PreviewSegmentVersionUseCaseProtocol(Protocol):
    """Use case port for previewing exact segment version."""

    async def __call__(
        self,
        query: PreviewSegmentVersionQuery,
    ) -> SegmentPreviewDTO:
        """Returns read-only preview for exact segment version."""
        ...


class PreviewSegmentVersionUseCase:
    """Previews exact Contact segment version."""

    def __init__(
        self,
        *,
        evaluation_service: SegmentVersionEvaluationService,
        contact_lookup: ContactLookupProtocol,
    ) -> None:
        self._evaluation_service = evaluation_service
        self._contact_lookup = contact_lookup

    async def __call__(
        self,
        query: PreviewSegmentVersionQuery,
    ) -> SegmentPreviewDTO:
        options = build_preview_options(
            limit=query.limit,
            offset=query.offset,
        )
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
    "PreviewSegmentVersionUseCase",
    "PreviewSegmentVersionUseCaseProtocol",
]
