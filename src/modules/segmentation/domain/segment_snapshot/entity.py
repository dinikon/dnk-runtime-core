from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_snapshot.error import (
    InvalidSegmentSnapshotError,
    SegmentSnapshotImmutableError,
    SegmentSnapshotTransitionError,
)
from src.modules.segmentation.domain.segment_snapshot.value_object import (
    SegmentSnapshotIdVO,
    SegmentSnapshotStatusVO,
)
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO


@dataclass(frozen=True, slots=True)
class SegmentSnapshot:
    """Frozen segment audience snapshot."""

    segment_snapshot_id: SegmentSnapshotIdVO
    segment_id: SegmentIdVO
    segment_version_id: SegmentVersionIdVO
    status: SegmentSnapshotStatusVO
    member_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.segment_snapshot_id, SegmentSnapshotIdVO):
            object.__setattr__(
                self,
                "segment_snapshot_id",
                SegmentSnapshotIdVO.from_value(self.segment_snapshot_id),
            )
        if not isinstance(self.segment_id, SegmentIdVO):
            object.__setattr__(
                self,
                "segment_id",
                SegmentIdVO.from_value(self.segment_id),
            )
        if not isinstance(self.segment_version_id, SegmentVersionIdVO):
            object.__setattr__(
                self,
                "segment_version_id",
                SegmentVersionIdVO.from_value(self.segment_version_id),
            )
        object.__setattr__(self, "status", SegmentSnapshotStatusVO(self.status))
        if self.member_count < 0:
            raise InvalidSegmentSnapshotError(
                "Segment snapshot member count must be >= 0."
            )
        if self.status == SegmentSnapshotStatusVO.FAILED:
            self._validate_failure_payload(
                error_code=self.error_code,
                error_message=self.error_message,
            )

    def start(self, *, now: datetime) -> "SegmentSnapshot":
        """Moves pending snapshot to running."""
        self._ensure_not_completed()
        if self.status != SegmentSnapshotStatusVO.PENDING:
            raise SegmentSnapshotTransitionError(
                "Only pending segment snapshot can be started."
            )
        return replace(
            self,
            status=SegmentSnapshotStatusVO.RUNNING,
            started_at=now,
        )

    def complete(self, *, now: datetime, member_count: int) -> "SegmentSnapshot":
        """Completes a running snapshot."""
        self._ensure_not_completed()
        if self.status != SegmentSnapshotStatusVO.RUNNING:
            raise SegmentSnapshotTransitionError(
                "Only running segment snapshot can be completed."
            )
        if member_count < 0:
            raise InvalidSegmentSnapshotError(
                "Segment snapshot member count must be >= 0."
            )
        return replace(
            self,
            status=SegmentSnapshotStatusVO.COMPLETED,
            member_count=member_count,
            completed_at=now,
        )

    def fail(
        self,
        *,
        now: datetime,
        error_code: str,
        error_message: str,
    ) -> "SegmentSnapshot":
        """Fails pending or running snapshot."""
        self._ensure_not_completed()
        if self.status not in {
            SegmentSnapshotStatusVO.PENDING,
            SegmentSnapshotStatusVO.RUNNING,
        }:
            raise SegmentSnapshotTransitionError(
                "Only pending or running segment snapshot can be failed."
            )
        self._validate_failure_payload(
            error_code=error_code,
            error_message=error_message,
        )
        return replace(
            self,
            status=SegmentSnapshotStatusVO.FAILED,
            completed_at=now,
            error_code=error_code.strip(),
            error_message=error_message.strip(),
        )

    def _ensure_not_completed(self) -> None:
        if self.status == SegmentSnapshotStatusVO.COMPLETED:
            raise SegmentSnapshotImmutableError(
                "Completed segment snapshot cannot be changed."
            )

    @staticmethod
    def _validate_failure_payload(
        *,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        if not isinstance(error_code, str) or not error_code.strip():
            raise InvalidSegmentSnapshotError(
                "Failed segment snapshot requires error code."
            )
        if not isinstance(error_message, str) or not error_message.strip():
            raise InvalidSegmentSnapshotError(
                "Failed segment snapshot requires error message."
            )


__all__ = ["SegmentSnapshot"]
