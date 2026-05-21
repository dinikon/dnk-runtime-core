from __future__ import annotations

from types import SimpleNamespace
import unittest
from uuid import uuid4

from fastapi import HTTPException

from src.modules.contact_point.application import (
    AttachContactPointResultDTO,
    DetachContactPointResultDTO,
)
from src.modules.contact_point.domain import (
    ContactPointBindingNotFoundError,
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
from src.modules.contact_point.presentation.http.requests import (
    AttachContactPointRequestSchema,
    DetachContactPointRequestSchema,
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


class ContactPointHttpRouterTests(unittest.TestCase):
    def test_router_exposes_action_endpoints(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/contact-points/attach"), routes)
        self.assertIn(("POST", "/contact-points/detach"), routes)


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


__all__ = [
    "ContactPointControllerTests",
    "ContactPointHttpRouterTests",
]
