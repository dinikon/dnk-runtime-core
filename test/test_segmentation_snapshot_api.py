from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from src.modules.segmentation.application.segment_snapshot import SegmentSnapshotDTO
from src.modules.segmentation.application.segment_snapshot_member import (
    SegmentSnapshotMemberDTO,
)
from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)
from src.modules.segmentation.application.segment_version import (
    SegmentVersionActiveVersionNotFoundError,
)
from src.modules.segmentation.domain.segment_snapshot import (
    SegmentSnapshotNotFoundError,
)
from src.modules.segmentation.presentation.http.router import router
from src.modules.segmentation.presentation.http.segment_snapshot.controllers.create_segment_snapshot import (
    create_segment_snapshot,
)
from src.modules.segmentation.presentation.http.segment_snapshot.controllers.get_segment_snapshot import (
    get_segment_snapshot,
)
from src.modules.segmentation.presentation.http.segment_snapshot.controllers.list_segment_snapshots import (
    list_segment_snapshots,
)
from src.modules.segmentation.presentation.http.segment_snapshot.requests import (
    CreateSegmentSnapshotRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_snapshot_member.controllers.list_segment_snapshot_members import (
    list_segment_snapshot_members,
)
from src.modules.shared import EntityIdVO


class _UseCaseStub:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self.result = result
        self.exc = exc
        self.command = None

    async def __call__(self, command):
        self.command = command
        if self.exc is not None:
            raise self.exc
        return self.result


def _context(tenant_id):
    return SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id))


def _snapshot_dto() -> SegmentSnapshotDTO:
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    return SegmentSnapshotDTO(
        id=uuid4(),
        segment_id=uuid4(),
        segment_version_id=uuid4(),
        status="completed",
        member_count=1,
        started_at=now,
        completed_at=now,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )


class SegmentationSnapshotApiTests(unittest.IsolatedAsyncioTestCase):
    def test_router_exposes_snapshot_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/segments/{segment_id}/snapshots"), routes)
        self.assertIn(("GET", "/segments/{segment_id}/snapshots"), routes)
        self.assertIn(("GET", "/segments/snapshots/{segment_snapshot_id}"), routes)
        self.assertIn(
            ("GET", "/segments/snapshots/{segment_snapshot_id}/members"),
            routes,
        )

    async def test_create_snapshot_maps_command_and_response(self) -> None:
        tenant_id = uuid4()
        segment_id = uuid4()
        version_id = uuid4()
        dto = _snapshot_dto()
        use_case = _UseCaseStub(dto)

        response = await create_segment_snapshot(
            segment_id=segment_id,
            payload=CreateSegmentSnapshotRequestSchema(
                segment_version_id=version_id,
            ),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(use_case.command.tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(use_case.command.segment_id.uuid, segment_id)
        self.assertEqual(use_case.command.segment_version_id.uuid, version_id)
        self.assertEqual(response.id, dto.id)
        self.assertEqual(response.status, "completed")

    async def test_get_and_list_snapshot_map_response(self) -> None:
        tenant_id = uuid4()
        snapshot_id = uuid4()
        segment_id = uuid4()
        dto = _snapshot_dto()

        get_response = await get_segment_snapshot(
            segment_snapshot_id=snapshot_id,
            context=_context(tenant_id),
            use_case=_UseCaseStub(dto),
        )
        list_response = await list_segment_snapshots(
            segment_id=segment_id,
            context=_context(tenant_id),
            use_case=_UseCaseStub([dto]),
            limit=50,
            offset=0,
        )

        self.assertEqual(get_response.id, dto.id)
        self.assertEqual(list_response.count, 1)
        self.assertEqual(
            list_response.items[0].segment_version_id, dto.segment_version_id
        )

    async def test_list_snapshot_members_maps_contact_only_response(self) -> None:
        tenant_id = uuid4()
        snapshot_id = uuid4()
        contact_id = uuid4()
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        member = SegmentSnapshotMemberDTO(
            id=uuid4(),
            segment_snapshot_id=snapshot_id,
            contact_id=contact_id,
            position=0,
            created_at=now,
            contact=ContactSummaryDTO(
                id=contact_id,
                first_name="Denis",
                last_name=None,
                middle_name=None,
                status="active",
            ),
        )

        response = await list_segment_snapshot_members(
            segment_snapshot_id=snapshot_id,
            context=_context(tenant_id),
            use_case=_UseCaseStub([member]),
            limit=50,
            offset=0,
            include_contact_summary=True,
        )

        payload = response.model_dump()
        self.assertEqual(response.items[0].contact_id, contact_id)
        self.assertEqual(response.items[0].contact.first_name, "Denis")
        self.assertNotIn("target_object_id", payload["items"][0])
        self.assertNotIn("target_record_id", payload["items"][0])

    async def test_snapshot_controllers_map_auth_and_errors(self) -> None:
        with self.assertRaises(HTTPException) as unauthorized:
            await create_segment_snapshot(
                segment_id=uuid4(),
                payload=CreateSegmentSnapshotRequestSchema(),
                context=SimpleNamespace(principal=None),
                use_case=_UseCaseStub(),
            )
        self.assertEqual(unauthorized.exception.status_code, 401)

        with self.assertRaises(HTTPException) as not_found:
            await get_segment_snapshot(
                segment_snapshot_id=uuid4(),
                context=_context(uuid4()),
                use_case=_UseCaseStub(exc=SegmentSnapshotNotFoundError(str(uuid4()))),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await create_segment_snapshot(
                segment_id=uuid4(),
                payload=CreateSegmentSnapshotRequestSchema(),
                context=_context(uuid4()),
                use_case=_UseCaseStub(
                    exc=SegmentVersionActiveVersionNotFoundError(str(uuid4()))
                ),
            )
        self.assertEqual(conflict.exception.status_code, 409)


__all__ = ["SegmentationSnapshotApiTests"]
