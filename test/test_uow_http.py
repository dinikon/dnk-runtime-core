"""Общий HTTP UoW завершает транзакцию до успешного ответа."""

import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from src.modules.shared.presentation.persistence.depends import UoWDep


class HttpUnitOfWorkTests(unittest.IsolatedAsyncioTestCase):
    async def test_commit_failure_is_not_reported_as_success_and_closes_session(self):
        session = SimpleNamespace(
            commit=AsyncMock(side_effect=RuntimeError("test commit failure")),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        app = FastAPI()
        app.state.db = lambda: session

        @app.post("/write")
        async def write(uow: UoWDep):
            self.assertIs(uow.session, session)
            return {"saved": True}

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="https://test",
        ) as client:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await client.post("/write")
        self.assertEqual(response.status_code, 500)
        session.commit.assert_awaited_once()
        session.rollback.assert_awaited_once()
        session.close.assert_awaited_once()
