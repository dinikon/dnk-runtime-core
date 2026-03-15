from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from starlette.requests import Request

from src.modules.shared.depends.authorization import (
    default_authorization_service,
    get_authorization_service,
)
from src.modules.shared.depends.clock import default_clock, get_clock
from src.modules.shared.kernel.access.ports import AuthorizationServiceProtocol
from src.modules.shared.kernel.time.ports import ClockPort


def _build_request(app: FastAPI) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "app": app,
    }
    return Request(scope)


class FixedClock(ClockPort):
    def __init__(self, value: datetime):
        self._value = value

    def now(self) -> datetime:
        return self._value


class DenyAllAuthorizationService(AuthorizationServiceProtocol):
    async def can(
        self,
        *,
        user_id: UUID | None,
        tenant_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
    ) -> bool:
        return False


class TestSharedCommonDepends(unittest.IsolatedAsyncioTestCase):

    def test_clock_uses_default_when_state_is_not_set(self) -> None:
        app = FastAPI()
        request = _build_request(app)

        clock = get_clock(request)

        self.assertIs(clock, default_clock)
        self.assertIsNotNone(clock.now().tzinfo)

    def test_clock_uses_state_override(self) -> None:
        app = FastAPI()
        fixed = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        app.state.clock = fixed
        request = _build_request(app)

        clock = get_clock(request)

        self.assertIs(clock, fixed)
        self.assertEqual(clock.now(), datetime(2026, 1, 1, tzinfo=UTC))

    async def test_authorization_uses_default_when_state_is_not_set(self) -> None:
        app = FastAPI()
        request = _build_request(app)

        service = get_authorization_service(request)

        self.assertIs(service, default_authorization_service)
        self.assertTrue(
            await service.can(
                user_id=None,
                tenant_id=None,
                action="action",
                resource_type="resource",
            )
        )

    async def test_authorization_uses_state_override(self) -> None:
        app = FastAPI()
        override = DenyAllAuthorizationService()
        app.state.authorization_service = override
        request = _build_request(app)

        service = get_authorization_service(request)

        self.assertIs(service, override)
        self.assertFalse(
            await service.can(
                user_id=None,
                tenant_id=None,
                action="action",
                resource_type="resource",
            )
        )
