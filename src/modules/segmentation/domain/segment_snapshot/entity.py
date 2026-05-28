from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Self

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

    @classmethod
    def create(
        cls,
        *,
        segment_snapshot_id: SegmentSnapshotIdVO,
        segment_id: SegmentIdVO,
        segment_version_id: SegmentVersionIdVO,
        status: SegmentSnapshotStatusVO = SegmentSnapshotStatusVO.PENDING,
        member_count: int = 0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> Self:
        """Creates snapshot from already prepared value objects."""
        if member_count < 0:
            raise InvalidSegmentSnapshotError(
                "Segment snapshot member count must be >= 0."
            )
        if status == SegmentSnapshotStatusVO.FAILED:
            cls._validate_failure_payload(
                error_code=error_code,
                error_message=error_message,
            )
        return cls(
            segment_snapshot_id=segment_snapshot_id,
            segment_id=segment_id,
            segment_version_id=segment_version_id,
            status=status,
            member_count=member_count,
            started_at=started_at,
            completed_at=completed_at,
            error_code=error_code,
            error_message=error_message,
        )

    def start(self, *, now: datetime) -> "SegmentSnapshot":
        """Moves pending snapshot to running."""
        self._ensure_not_completed()
        if self.status != SegmentSnapshotStatusVO.PENDING:
            raise SegmentSnapshotTransitionError(
                "Only pending segment snapshot can be started."
            )
        return SegmentSnapshot.create(
            segment_snapshot_id=self.segment_snapshot_id,
            segment_id=self.segment_id,
            segment_version_id=self.segment_version_id,
            status=SegmentSnapshotStatusVO.RUNNING,
            member_count=self.member_count,
            started_at=now,
            completed_at=self.completed_at,
            error_code=self.error_code,
            error_message=self.error_message,
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
        return SegmentSnapshot.create(
            segment_snapshot_id=self.segment_snapshot_id,
            segment_id=self.segment_id,
            segment_version_id=self.segment_version_id,
            status=SegmentSnapshotStatusVO.COMPLETED,
            member_count=member_count,
            started_at=self.started_at,
            completed_at=now,
            error_code=self.error_code,
            error_message=self.error_message,
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
        return SegmentSnapshot.create(
            segment_snapshot_id=self.segment_snapshot_id,
            segment_id=self.segment_id,
            segment_version_id=self.segment_version_id,
            status=SegmentSnapshotStatusVO.FAILED,
            member_count=self.member_count,
            started_at=self.started_at,
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
