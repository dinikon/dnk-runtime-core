from __future__ import annotations

import unittest
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlparse

from src.modules.shorter.application.redirect.command import (
    AddRedirectCommand,
    DeleteRedirectCommand,
    UpdateRedirectCommand,
)
from src.modules.shorter.application.redirect.query import (
    GetRedirectQuery,
    ListRedirectQuery,
)
from src.modules.shorter.application.redirect.use_case import (
    AddRedirectUseCase,
    DeleteRedirectUseCase,
    GetRedirectUseCase,
    ListRedirectUseCase,
    UpdateRedirectUseCase,
)
from src.modules.shorter.domain.errors import (
    RedirectNotFoundError,
    RedirectTargetUrlInvalidError,
)
from src.modules.shorter.domain.redirect import (
    RedirectEntity,
    RedirectTargetUrlVO,
    RedirectUtmParametersVO,
)


class _FixedClock:
    def __init__(self, now_value: datetime):
        self._now_value = now_value

    def now(self) -> datetime:
        return self._now_value


class _InMemoryRedirectRepository:
    def __init__(self):
        self._items: dict[object, RedirectEntity] = {}

    async def save(self, redirect: RedirectEntity) -> None:
        self._items[redirect.id.value] = redirect

    async def get_by_id(self, *, redirect_id):
        return self._items.get(redirect_id.value)

    async def list(self) -> tuple[RedirectEntity, ...]:
        return tuple(self._items.values())

    async def delete_by_id(self, *, redirect_id) -> bool:
        return self._items.pop(redirect_id.value, None) is not None


def _query_params(url: str) -> dict[str, str]:
    return dict(parse_qsl(urlparse(url).query, keep_blank_values=True))


class TestRedirectEntity(unittest.TestCase):
    def test_target_url_requires_https_scheme(self) -> None:
        with self.assertRaises(RedirectTargetUrlInvalidError):
            RedirectTargetUrlVO("http://example.com/landing")

    def test_resolve_target_url_overrides_only_existing_utm_tags(self) -> None:
        redirect = RedirectEntity.create(
            target_url=RedirectTargetUrlVO(
                "https://example.com/landing?foo=1&utm_source=target-source&utm_medium=target-medium"
            ),
            utm_parameters=RedirectUtmParametersVO(
                utm_source="configured-source",
                utm_campaign="configured-campaign",
            ),
            is_override=True,
            is_append=False,
            created_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
        )

        resolved = redirect.resolve_target_url(
            short_link_query_params={
                "utm_source": "incoming-source",
                "utm_medium": "incoming-medium",
                "utm_term": "incoming-term",
                "non_utm": "ignored",
            }
        )
        query = _query_params(resolved)

        self.assertEqual(query["foo"], "1")
        self.assertEqual(query["utm_source"], "incoming-source")
        self.assertEqual(query["utm_medium"], "incoming-medium")
        self.assertEqual(query["utm_campaign"], "configured-campaign")
        self.assertNotIn("utm_term", query)
        self.assertNotIn("non_utm", query)

    def test_resolve_target_url_appends_missing_utm_tags(self) -> None:
        redirect = RedirectEntity.create(
            target_url=RedirectTargetUrlVO(
                "https://example.com/landing?utm_source=target-source"
            ),
            utm_parameters=RedirectUtmParametersVO(
                utm_campaign="configured-campaign",
            ),
            is_override=False,
            is_append=True,
            created_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
        )

        resolved = redirect.resolve_target_url(
            short_link_query_params={
                "utm_source": "incoming-source",
                "utm_term": "incoming-term",
            }
        )
        query = _query_params(resolved)

        self.assertEqual(query["utm_source"], "target-source")
        self.assertEqual(query["utm_campaign"], "configured-campaign")
        self.assertEqual(query["utm_term"], "incoming-term")


class TestRedirectCrudUseCases(unittest.IsolatedAsyncioTestCase):
    async def test_add_get_list_update_delete_flow(self) -> None:
        repository = _InMemoryRedirectRepository()
        created_at = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
        updated_at = datetime(2026, 3, 12, 13, 0, tzinfo=UTC)

        add_use_case = AddRedirectUseCase(
            clock=_FixedClock(created_at),
            redirect_repository=repository,
        )
        added = await add_use_case.execute(
            AddRedirectCommand(
                target_url="https://example.com/landing",
                utm_source="newsletter",
                utm_campaign="spring-launch",
                is_override=True,
            )
        )

        get_use_case = GetRedirectUseCase(redirect_repository=repository)
        fetched = await get_use_case.execute(
            GetRedirectQuery(redirect_id=added.redirect_id)
        )
        self.assertEqual(fetched.redirect_id, added.redirect_id)
        self.assertEqual(fetched.target_url, "https://example.com/landing")
        self.assertEqual(fetched.utm_source, "newsletter")
        self.assertTrue(fetched.is_override)
        self.assertFalse(fetched.is_append)

        list_use_case = ListRedirectUseCase(redirect_repository=repository)
        listed = await list_use_case.execute(ListRedirectQuery())
        self.assertEqual(len(listed.items), 1)
        self.assertEqual(listed.items[0].redirect_id, added.redirect_id)

        update_use_case = UpdateRedirectUseCase(
            clock=_FixedClock(updated_at),
            redirect_repository=repository,
        )
        updated = await update_use_case.execute(
            UpdateRedirectCommand(
                redirect_id=added.redirect_id,
                target_url="https://example.com/updated",
                utm_medium="cpc",
                utm_content="hero-banner",
                is_override=False,
                is_append=True,
            )
        )
        self.assertEqual(updated.target_url, "https://example.com/updated")
        self.assertIsNone(updated.utm_source)
        self.assertEqual(updated.utm_medium, "cpc")
        self.assertEqual(updated.utm_content, "hero-banner")
        self.assertFalse(updated.is_override)
        self.assertTrue(updated.is_append)
        self.assertEqual(updated.created_at, created_at)
        self.assertEqual(updated.updated_at, updated_at)

        delete_use_case = DeleteRedirectUseCase(redirect_repository=repository)
        deleted = await delete_use_case.execute(
            DeleteRedirectCommand(redirect_id=added.redirect_id)
        )
        self.assertEqual(deleted.redirect_id, added.redirect_id)

        with self.assertRaises(RedirectNotFoundError):
            await get_use_case.execute(GetRedirectQuery(redirect_id=added.redirect_id))


if __name__ == "__main__":
    unittest.main()
