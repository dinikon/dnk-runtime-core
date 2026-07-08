from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from uuid import uuid4

from fastapi import HTTPException

from src.modules.contact_point.application import (
    AttachContactPointResultDTO,
    ContactPointBindingDTO,
    ContactPointBindingListDTO,
    ContactPointDTO,
    ContactPointListDTO,
    DetachContactPointResultDTO,
    OwnerContactPointDTO,
    OwnerContactPointListDTO,
)
from src.modules.contact_point.domain import (
    ContactPointBindingNotFoundError,
    ContactPointNotFoundError,
    ContactPointOwnerNotFoundError,
    ContactPointTypeVO,
    InvalidContactPointValueError,
)
from src.modules.contact_point.presentation.http.controllers.attach_contact_point import (
    attach_contact_point,
)
from src.modules.contact_point.presentation.http.controllers.detach_contact_point import (
    detach_contact_point,
)
from src.modules.contact_point.presentation.http.controllers.get_contact_point import (
    get_contact_point,
)
from src.modules.contact_point.presentation.http.controllers.list_contact_point_bindings import (
    list_contact_point_bindings,
)
from src.modules.contact_point.presentation.http.controllers.list_contact_points import (
    list_contact_points,
)
from src.modules.contact_point.presentation.http.controllers.list_owner_contact_points import (
    list_owner_contact_points,
    list_owner_contact_points_by_path,
)
from src.modules.contact_point.presentation.http.requests import (
    AttachContactPointRequestSchema,
    DetachContactPointRequestSchema,
    ListOwnerContactPointsRequestSchema,
)
from src.modules.contact_point.presentation.http.router import router
from src.modules.runtime_data.domain.error import RuntimeDataPersistenceError
from src.modules.shared import EntityIdVO


class _UseCase:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self.result = result
        self.exc = exc
        self.command = None

    async def __call__(self, command):
        self.command = command
        if self.exc is not None:
            raise self.exc
        return self.result


def _context(tenant_id=None):
    return SimpleNamespace(
        principal=SimpleNamespace(
            tenant_id=tenant_id if tenant_id is not None else uuid4()
        )
    )


class ContactPointControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_attach_success_uses_tenant_context_and_returns_response(
        self,
    ) -> None:
        tenant_id = uuid4()
        owner_object_id = uuid4()
        owner_record_id = uuid4()
        contact_point_id = uuid4()
        binding_id = uuid4()
        use_case = _UseCase(
            AttachContactPointResultDTO(
                contact_point_id=contact_point_id,
                binding_id=binding_id,
                contact_point_created=True,
                binding_created=True,
                already_attached=False,
            )
        )

        response = await attach_contact_point(
            payload=AttachContactPointRequestSchema(
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="user@example.com",
                is_primary=True,
            ),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(response.contact_point_id, contact_point_id)
        self.assertEqual(response.binding_id, binding_id)
        self.assertIs(type(use_case.command.tenant_id), EntityIdVO)
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.command.owner_object_id.uuid, owner_object_id)
        self.assertTrue(use_case.command.is_primary)

    async def test_detach_success_uses_tenant_context_and_returns_response(
        self,
    ) -> None:
        tenant_id = uuid4()
        contact_point_id = uuid4()
        binding_id = uuid4()
        use_case = _UseCase(
            DetachContactPointResultDTO(
                contact_point_id=contact_point_id,
                binding_id=binding_id,
                binding_deleted=True,
                contact_point_deleted=False,
                contact_point_left_orphan=True,
            )
        )

        response = await detach_contact_point(
            payload=DetachContactPointRequestSchema(binding_id=binding_id),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(response.binding_id, binding_id)
        self.assertFalse(response.contact_point_deleted)
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.command.binding_id.uuid, binding_id)

    async def test_list_by_record_success_uses_body_and_returns_response(self) -> None:
        tenant_id = uuid4()
        owner_object_id = uuid4()
        owner_record_id = uuid4()
        binding_id = uuid4()
        contact_point_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        use_case = _UseCase(
            OwnerContactPointListDTO(
                items=(
                    OwnerContactPointDTO(
                        binding_id=binding_id,
                        contact_point_id=contact_point_id,
                        contact_point_type=ContactPointTypeVO.EMAIL,
                        raw_value="User@Example.COM",
                        normalized_value="user@example.com",
                        is_primary=True,
                        is_active=True,
                        detached_at=None,
                        created_at=now,
                        updated_at=now,
                    ),
                ),
                count=1,
            )
        )

        response = await list_owner_contact_points(
            payload=ListOwnerContactPointsRequestSchema(
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
            ),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(response.count, 1)
        self.assertEqual(response.items[0].binding_id, binding_id)
        self.assertEqual(response.items[0].normalized_value, "user@example.com")
        self.assertTrue(response.items[0].is_active)
        self.assertIsNone(response.items[0].detached_at)
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.command.owner_object_id.uuid, owner_object_id)
        self.assertEqual(use_case.command.owner_record_id.uuid, owner_record_id)

    async def test_get_contact_point_success_uses_path_and_returns_response(
        self,
    ) -> None:
        tenant_id = uuid4()
        contact_point_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        use_case = _UseCase(
            ContactPointDTO(
                id=contact_point_id,
                created_at=now,
                updated_at=now,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="User@Example.COM",
                normalized_value="user@example.com",
            )
        )

        response = await get_contact_point(
            contact_point_id=contact_point_id,
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(response.id, contact_point_id)
        self.assertEqual(response.normalized_value, "user@example.com")
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.command.contact_point_id.uuid, contact_point_id)

    async def test_list_contact_points_success_uses_query_params(self) -> None:
        tenant_id = uuid4()
        contact_point_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        use_case = _UseCase(
            ContactPointListDTO(
                items=(
                    ContactPointDTO(
                        id=contact_point_id,
                        created_at=now,
                        updated_at=now,
                        contact_point_type=ContactPointTypeVO.PHONE,
                        raw_value="+380671112233",
                        normalized_value="+380671112233",
                    ),
                ),
                count=1,
                limit=25,
                offset=5,
            )
        )

        response = await list_contact_points(
            context=_context(tenant_id),
            use_case=use_case,
            contact_point_type=ContactPointTypeVO.PHONE,
            limit=25,
            offset=5,
        )

        self.assertEqual(response.count, 1)
        self.assertEqual(response.limit, 25)
        self.assertEqual(response.offset, 5)
        self.assertEqual(response.items[0].id, contact_point_id)
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.command.contact_point_type, ContactPointTypeVO.PHONE)
        self.assertEqual(use_case.command.limit, 25)
        self.assertEqual(use_case.command.offset, 5)

    async def test_list_owner_contact_points_get_success_uses_path_and_query(
        self,
    ) -> None:
        tenant_id = uuid4()
        owner_object_id = uuid4()
        owner_record_id = uuid4()
        binding_id = uuid4()
        contact_point_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        use_case = _UseCase(
            OwnerContactPointListDTO(
                items=(
                    OwnerContactPointDTO(
                        binding_id=binding_id,
                        contact_point_id=contact_point_id,
                        contact_point_type=ContactPointTypeVO.EMAIL,
                        raw_value="User@Example.COM",
                        normalized_value="user@example.com",
                        is_primary=True,
                        is_active=True,
                        detached_at=None,
                        created_at=now,
                        updated_at=now,
                    ),
                ),
                count=1,
                limit=10,
                offset=2,
            )
        )

        response = await list_owner_contact_points_by_path(
            owner_object_id=owner_object_id,
            owner_record_id=owner_record_id,
            context=_context(tenant_id),
            use_case=use_case,
            contact_point_type=ContactPointTypeVO.EMAIL,
            limit=10,
            offset=2,
        )

        self.assertEqual(response.count, 1)
        self.assertEqual(response.limit, 10)
        self.assertEqual(response.offset, 2)
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.command.owner_object_id.uuid, owner_object_id)
        self.assertEqual(use_case.command.owner_record_id.uuid, owner_record_id)
        self.assertEqual(use_case.command.contact_point_type, ContactPointTypeVO.EMAIL)

    async def test_list_bindings_success_uses_query_params(self) -> None:
        tenant_id = uuid4()
        owner_object_id = uuid4()
        owner_record_id = uuid4()
        contact_point_id = uuid4()
        binding_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        use_case = _UseCase(
            ContactPointBindingListDTO(
                items=(
                    ContactPointBindingDTO(
                        id=binding_id,
                        contact_point_id=contact_point_id,
                        contact_point_type=ContactPointTypeVO.EMAIL,
                        owner_object_id=owner_object_id,
                        owner_record_id=owner_record_id,
                        is_primary=True,
                        is_active=False,
                        detached_at=now,
                        created_at=now,
                        updated_at=now,
                    ),
                ),
                count=1,
                limit=20,
                offset=3,
            )
        )

        response = await list_contact_point_bindings(
            context=_context(tenant_id),
            use_case=use_case,
            contact_point_type=ContactPointTypeVO.EMAIL,
            contact_point_id=contact_point_id,
            owner_object_id=owner_object_id,
            owner_record_id=owner_record_id,
            is_active=False,
            limit=20,
            offset=3,
        )

        self.assertEqual(response.count, 1)
        self.assertEqual(response.items[0].id, binding_id)
        self.assertFalse(response.items[0].is_active)
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.command.contact_point_id.uuid, contact_point_id)
        self.assertEqual(use_case.command.owner_object_id.uuid, owner_object_id)
        self.assertEqual(use_case.command.owner_record_id.uuid, owner_record_id)
        self.assertEqual(use_case.command.is_active, False)

    async def test_controllers_return_401_without_tenant_context(self) -> None:
        with self.assertRaises(HTTPException) as attach_ctx:
            await attach_contact_point(
                payload=AttachContactPointRequestSchema(
                    owner_object_id=uuid4(),
                    owner_record_id=uuid4(),
                    contact_point_type=ContactPointTypeVO.EMAIL,
                    raw_value="user@example.com",
                ),
                context=SimpleNamespace(principal=SimpleNamespace(tenant_id=None)),
                use_case=_UseCase(),
            )

        self.assertEqual(attach_ctx.exception.status_code, 401)

        with self.assertRaises(HTTPException) as detach_ctx:
            await detach_contact_point(
                payload=DetachContactPointRequestSchema(binding_id=uuid4()),
                context=SimpleNamespace(principal=None),
                use_case=_UseCase(),
            )

        self.assertEqual(detach_ctx.exception.status_code, 401)

        with self.assertRaises(HTTPException) as list_ctx:
            await list_owner_contact_points(
                payload=ListOwnerContactPointsRequestSchema(
                    owner_object_id=uuid4(),
                    owner_record_id=uuid4(),
                ),
                context=SimpleNamespace(principal=None),
                use_case=_UseCase(),
            )

        self.assertEqual(list_ctx.exception.status_code, 401)

        with self.assertRaises(HTTPException) as get_ctx:
            await get_contact_point(
                contact_point_id=uuid4(),
                context=SimpleNamespace(principal=None),
                use_case=_UseCase(),
            )

        self.assertEqual(get_ctx.exception.status_code, 401)

        with self.assertRaises(HTTPException) as list_points_ctx:
            await list_contact_points(
                context=SimpleNamespace(principal=None),
                use_case=_UseCase(),
            )

        self.assertEqual(list_points_ctx.exception.status_code, 401)

        with self.assertRaises(HTTPException) as owner_get_ctx:
            await list_owner_contact_points_by_path(
                owner_object_id=uuid4(),
                owner_record_id=uuid4(),
                context=SimpleNamespace(principal=None),
                use_case=_UseCase(),
            )

        self.assertEqual(owner_get_ctx.exception.status_code, 401)

        with self.assertRaises(HTTPException) as bindings_ctx:
            await list_contact_point_bindings(
                context=SimpleNamespace(principal=None),
                use_case=_UseCase(),
            )

        self.assertEqual(bindings_ctx.exception.status_code, 401)

    async def test_attach_maps_404_409_and_422_errors(self) -> None:
        payload = AttachContactPointRequestSchema(
            owner_object_id=uuid4(),
            owner_record_id=uuid4(),
            contact_point_type=ContactPointTypeVO.EMAIL,
            raw_value="broken",
        )

        with self.assertRaises(HTTPException) as not_found:
            await attach_contact_point(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=ContactPointOwnerNotFoundError("o", "r")),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await attach_contact_point(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=RuntimeDataPersistenceError("db")),
            )
        self.assertEqual(conflict.exception.status_code, 409)

        with self.assertRaises(HTTPException) as invalid:
            await attach_contact_point(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=InvalidContactPointValueError("EMAIL", "broken")),
            )
        self.assertEqual(invalid.exception.status_code, 422)

    async def test_detach_maps_404_409_and_422_errors(self) -> None:
        payload = DetachContactPointRequestSchema(binding_id=uuid4())

        with self.assertRaises(HTTPException) as not_found:
            await detach_contact_point(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=ContactPointBindingNotFoundError("b")),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await detach_contact_point(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=RuntimeDataPersistenceError("db")),
            )
        self.assertEqual(conflict.exception.status_code, 409)

        with self.assertRaises(HTTPException) as invalid:
            await detach_contact_point(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=InvalidContactPointValueError("EMAIL", "bad")),
            )
        self.assertEqual(invalid.exception.status_code, 422)

    async def test_list_by_record_maps_404_409_and_422_errors(self) -> None:
        payload = ListOwnerContactPointsRequestSchema(
            owner_object_id=uuid4(),
            owner_record_id=uuid4(),
        )

        with self.assertRaises(HTTPException) as not_found:
            await list_owner_contact_points(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=ContactPointOwnerNotFoundError("o", "r")),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as missing_contact_point:
            await list_owner_contact_points(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=ContactPointNotFoundError("c")),
            )
        self.assertEqual(missing_contact_point.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await list_owner_contact_points(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=RuntimeDataPersistenceError("db")),
            )
        self.assertEqual(conflict.exception.status_code, 409)

        with self.assertRaises(HTTPException) as invalid:
            await list_owner_contact_points(
                payload=payload,
                context=_context(),
                use_case=_UseCase(exc=InvalidContactPointValueError("EMAIL", "bad")),
            )
        self.assertEqual(invalid.exception.status_code, 422)

    async def test_list_owner_contact_points_get_maps_404_409_and_422_errors(
        self,
    ) -> None:
        with self.assertRaises(HTTPException) as not_found:
            await list_owner_contact_points_by_path(
                owner_object_id=uuid4(),
                owner_record_id=uuid4(),
                context=_context(),
                use_case=_UseCase(exc=ContactPointOwnerNotFoundError("o", "r")),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as missing_contact_point:
            await list_owner_contact_points_by_path(
                owner_object_id=uuid4(),
                owner_record_id=uuid4(),
                context=_context(),
                use_case=_UseCase(exc=ContactPointNotFoundError("c")),
            )
        self.assertEqual(missing_contact_point.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await list_owner_contact_points_by_path(
                owner_object_id=uuid4(),
                owner_record_id=uuid4(),
                context=_context(),
                use_case=_UseCase(exc=RuntimeDataPersistenceError("db")),
            )
        self.assertEqual(conflict.exception.status_code, 409)

        with self.assertRaises(HTTPException) as invalid:
            await list_owner_contact_points_by_path(
                owner_object_id=uuid4(),
                owner_record_id=uuid4(),
                context=_context(),
                use_case=_UseCase(exc=InvalidContactPointValueError("EMAIL", "bad")),
            )
        self.assertEqual(invalid.exception.status_code, 422)

    async def test_get_contact_point_maps_404_409_and_422_errors(self) -> None:
        contact_point_id = uuid4()

        with self.assertRaises(HTTPException) as not_found:
            await get_contact_point(
                contact_point_id=contact_point_id,
                context=_context(),
                use_case=_UseCase(exc=ContactPointNotFoundError("c")),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await get_contact_point(
                contact_point_id=contact_point_id,
                context=_context(),
                use_case=_UseCase(exc=RuntimeDataPersistenceError("db")),
            )
        self.assertEqual(conflict.exception.status_code, 409)

        with self.assertRaises(HTTPException) as invalid:
            await get_contact_point(
                contact_point_id=contact_point_id,
                context=_context(),
                use_case=_UseCase(exc=InvalidContactPointValueError("EMAIL", "bad")),
            )
        self.assertEqual(invalid.exception.status_code, 422)

    async def test_list_contact_points_maps_404_409_and_422_errors(self) -> None:
        with self.assertRaises(HTTPException) as not_found:
            await list_contact_points(
                context=_context(),
                use_case=_UseCase(exc=ContactPointNotFoundError("c")),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await list_contact_points(
                context=_context(),
                use_case=_UseCase(exc=RuntimeDataPersistenceError("db")),
            )
        self.assertEqual(conflict.exception.status_code, 409)

        with self.assertRaises(HTTPException) as invalid:
            await list_contact_points(
                context=_context(),
                use_case=_UseCase(exc=InvalidContactPointValueError("EMAIL", "bad")),
            )
        self.assertEqual(invalid.exception.status_code, 422)

    async def test_list_bindings_maps_404_409_and_422_errors(self) -> None:
        with self.assertRaises(HTTPException) as not_found:
            await list_contact_point_bindings(
                context=_context(),
                use_case=_UseCase(exc=ContactPointBindingNotFoundError("b")),
            )
        self.assertEqual(not_found.exception.status_code, 404)

        with self.assertRaises(HTTPException) as conflict:
            await list_contact_point_bindings(
                context=_context(),
                use_case=_UseCase(exc=RuntimeDataPersistenceError("db")),
            )
        self.assertEqual(conflict.exception.status_code, 409)

        with self.assertRaises(HTTPException) as invalid:
            await list_contact_point_bindings(
                context=_context(),
                use_case=_UseCase(exc=InvalidContactPointValueError("EMAIL", "bad")),
            )
        self.assertEqual(invalid.exception.status_code, 422)


__all__ = [
    "ContactPointControllerTests",
    "ContactPointHttpRouterTests",
]
