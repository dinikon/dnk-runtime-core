from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.segmentation.domain.segment_definition import (
    InvalidSegmentDefinitionNameError,
    SegmentDefinition,
    SegmentDefinitionArchivedError,
    SegmentDefinitionKindChangeError,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_snapshot import (
    InvalidSegmentSnapshotError,
    SegmentSnapshot,
    SegmentSnapshotIdVO,
    SegmentSnapshotImmutableError,
    SegmentSnapshotStatusVO,
    SegmentSnapshotTransitionError,
)
from src.modules.segmentation.domain.segment_version import (
    InvalidSegmentVersionError,
    SegmentVersion,
    SegmentVersionIdVO,
    SegmentVersionStatusVO,
    SegmentVersionTransitionError,
)


class SegmentationLifecycleDomainTests(unittest.TestCase):
    def test_segment_definition_normalizes_name_and_rejects_blank(self) -> None:
        segment = SegmentDefinition(
            segment_id=SegmentIdVO.from_value(uuid4()),
            name="  VIP customers  ",
            segment_kind=SegmentKindVO.STATIC,
            status=SegmentStatusVO.DRAFT,
        )

        self.assertEqual(segment.name, "VIP customers")
        with self.assertRaises(InvalidSegmentDefinitionNameError):
            SegmentDefinition(
                segment_id=SegmentIdVO.from_value(uuid4()),
                name=" ",
                segment_kind=SegmentKindVO.STATIC,
                status=SegmentStatusVO.DRAFT,
            )

    def test_segment_definition_rejects_archived_update_and_kind_change(self) -> None:
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        segment = SegmentDefinition(
            segment_id=SegmentIdVO.from_value(uuid4()),
            name="VIP",
            segment_kind=SegmentKindVO.STATIC,
            status=SegmentStatusVO.ACTIVE,
        )

        with self.assertRaises(SegmentDefinitionKindChangeError):
            segment.update(segment_kind=SegmentKindVO.DYNAMIC)

        archived = segment.archive(now=now)
        self.assertIs(archived.archive(now=now), archived)
        with self.assertRaises(SegmentDefinitionArchivedError):
            archived.update(name="Archived VIP")

    def test_segment_version_validates_copies_and_transitions(self) -> None:
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        config = {"rules": [{"field": "status", "value": "active"}]}
        version = SegmentVersion(
            segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
            segment_id=SegmentIdVO.from_value(uuid4()),
            version_number=1,
            status=SegmentVersionStatusVO.DRAFT,
            config=config,
            config_checksum="abc",
        )
        config["rules"][0]["value"] = "inactive"

        self.assertEqual(version.config["rules"][0]["value"], "active")
        active = version.activate(now=now)
        self.assertEqual(active.status, SegmentVersionStatusVO.ACTIVE)
        self.assertEqual(active.activated_at, now)
        with self.assertRaises(SegmentVersionTransitionError):
            active.activate(now=now)
        archived = active.archive(now=now)
        self.assertIs(archived.archive(now=now), archived)

    def test_segment_version_rejects_invalid_number_config_and_checksum(self) -> None:
        with self.assertRaises(InvalidSegmentVersionError):
            SegmentVersion(
                segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
                segment_id=SegmentIdVO.from_value(uuid4()),
                version_number=0,
                status=SegmentVersionStatusVO.DRAFT,
                config={},
                config_checksum="abc",
            )
        with self.assertRaises(InvalidSegmentVersionError):
            SegmentVersion(
                segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
                segment_id=SegmentIdVO.from_value(uuid4()),
                version_number=1,
                status=SegmentVersionStatusVO.DRAFT,
                config=[],
                config_checksum="abc",
            )
        with self.assertRaises(InvalidSegmentVersionError):
            SegmentVersion(
                segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
                segment_id=SegmentIdVO.from_value(uuid4()),
                version_number=1,
                status=SegmentVersionStatusVO.DRAFT,
                config={},
                config_checksum=" ",
            )

    def test_segment_snapshot_allows_expected_transitions_only(self) -> None:
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        snapshot = SegmentSnapshot(
            segment_snapshot_id=SegmentSnapshotIdVO.from_value(uuid4()),
            segment_id=SegmentIdVO.from_value(uuid4()),
            segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
            status=SegmentSnapshotStatusVO.PENDING,
            member_count=0,
        )

        running = snapshot.start(now=now)
        completed = running.complete(now=now, member_count=10)
        self.assertEqual(completed.status, SegmentSnapshotStatusVO.COMPLETED)
        self.assertEqual(completed.member_count, 10)
        with self.assertRaises(SegmentSnapshotImmutableError):
            completed.fail(now=now, error_code="x", error_message="y")
        with self.assertRaises(SegmentSnapshotTransitionError):
            running.start(now=now)

    def test_segment_snapshot_failure_payload_and_member_count_validation(self) -> None:
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        snapshot = SegmentSnapshot(
            segment_snapshot_id=SegmentSnapshotIdVO.from_value(uuid4()),
            segment_id=SegmentIdVO.from_value(uuid4()),
            segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
            status=SegmentSnapshotStatusVO.PENDING,
            member_count=0,
        )

        failed = snapshot.fail(
            now=now,
            error_code=" eval ",
            error_message=" failed ",
        )
        self.assertEqual(failed.status, SegmentSnapshotStatusVO.FAILED)
        self.assertEqual(failed.error_code, "eval")
        with self.assertRaises(InvalidSegmentSnapshotError):
            snapshot.start(now=now).complete(now=now, member_count=-1)
        with self.assertRaises(InvalidSegmentSnapshotError):
            SegmentSnapshot(
                segment_snapshot_id=SegmentSnapshotIdVO.from_value(uuid4()),
                segment_id=SegmentIdVO.from_value(uuid4()),
                segment_version_id=SegmentVersionIdVO.from_value(uuid4()),
                status=SegmentSnapshotStatusVO.PENDING,
                member_count=-1,
            )


__all__ = ["SegmentationLifecycleDomainTests"]
