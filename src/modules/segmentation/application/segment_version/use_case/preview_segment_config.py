from typing import Protocol

from src.modules.segmentation.application.segment_static_member.query import (
    ContactLookupProtocol,
)
from src.modules.segmentation.application.segment_version.command import (
    PreviewSegmentConfigCommand,
)
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionDslConfigValidator,
)
from src.modules.segmentation.application.segment_version.dto import SegmentPreviewDTO
from src.modules.segmentation.application.segment_version.evaluation import (
    SegmentVersionEvaluationService,
)
from src.modules.segmentation.application.segment_version.use_case.preview_common import (
    build_preview_options,
    build_segment_preview_dto,
)


class PreviewSegmentConfigUseCaseProtocol(Protocol):
    """Use case port for previewing raw segment config."""

    async def __call__(
        self,
        command: PreviewSegmentConfigCommand,
    ) -> SegmentPreviewDTO:
        """Returns read-only preview for raw dynamic segment config."""
        ...


class PreviewSegmentConfigUseCase:
    """Previews raw Contact segment version DSL config."""

    def __init__(
        self,
        *,
        dsl_validator: SegmentVersionDslConfigValidator,
        evaluation_service: SegmentVersionEvaluationService,
        contact_lookup: ContactLookupProtocol,
    ) -> None:
        self._dsl_validator = dsl_validator
        self._evaluation_service = evaluation_service
        self._contact_lookup = contact_lookup

    async def __call__(
        self,
        command: PreviewSegmentConfigCommand,
    ) -> SegmentPreviewDTO:
        options = build_preview_options(
            limit=command.limit,
            offset=command.offset,
        )
        dsl_config = await self._dsl_validator.validate(
            tenant_id=command.tenant_id,
            config=command.config,
        )
        evaluation = await self._evaluation_service.evaluate_config(
            tenant_id=command.tenant_id,
            config=dsl_config,
            options=options,
        )
        return await build_segment_preview_dto(
            tenant_id=command.tenant_id,
            evaluation=evaluation,
            limit=command.limit,
            offset=command.offset,
            include_contact_summary=command.include_contact_summary,
            contact_lookup=self._contact_lookup,
        )


__all__ = [
    "PreviewSegmentConfigUseCase",
    "PreviewSegmentConfigUseCaseProtocol",
]
