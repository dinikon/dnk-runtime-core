"""Правила справочника локалей и сценарии без инфраструктурных зависимостей."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant_locale.command.add_tenant_locale.command import (
    AddTenantLocaleCommand,
)
from src.modules.tenancy.application.tenant_locale.command.add_tenant_locale.handler import (
    AddTenantLocaleHandler,
)
from src.modules.tenancy.application.tenant_locale.command.remove_tenant_locale.command import (
    RemoveTenantLocaleCommand,
)
from src.modules.tenancy.application.tenant_locale.command.remove_tenant_locale.handler import (
    RemoveTenantLocaleHandler,
)
from src.modules.tenancy.application.tenant_locale.query.list_system_locales.handler import (
    ListSystemLocalesHandler,
)
from src.modules.tenancy.application.tenant_locale.query.is_tenant_locale_selected.handler import (
    IsTenantLocaleSelectedHandler,
)
from src.modules.tenancy.application.tenant_locale.query.is_tenant_locale_selected.query import (
    IsTenantLocaleSelectedQuery,
)
from src.modules.tenancy.application.tenant_locale.query.list_system_locales.query import (
    ListSystemLocalesQuery,
)
from src.modules.tenancy.domain.tenant_locale.error import (
    InvalidTenantLocaleError,
    TenantLocaleNotSelectedError,
)
from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)


class TenantLocaleDomainTests(unittest.TestCase):
    def test_only_system_codes_are_accepted_and_value_is_immutable(self):
        for code in ("uk", "en"):
            self.assertEqual(TenantLocaleCodeVO(code).value, code)
        for code in ("", "UK", " uk ", "de", None, 3):
            with self.subTest(code=code), self.assertRaises(InvalidTenantLocaleError):
                TenantLocaleCodeVO(code)
        with self.assertRaises(FrozenInstanceError):
            TenantLocaleCodeVO("uk").value = "en"


class TenantLocaleApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_validates_before_write_and_preserves_audit(self):
        repository = Mock(add=AsyncMock())
        actor = EntityIdVO(uuid4())
        now = datetime(2026, 10, 5, tzinfo=UTC)
        clock = Mock(now=Mock(return_value=now))
        handler = AddTenantLocaleHandler(repository, clock)

        result = await handler.execute(AddTenantLocaleCommand("uk", actor))
        self.assertEqual(
            (result.code, result.created_at, result.created_by), ("uk", now, actor.uuid)
        )
        saved = repository.add.await_args.args[0]
        self.assertEqual(
            (saved.code.value, saved.created_at, saved.created_by), ("uk", now, actor)
        )
        clock.now.assert_called_once_with()
        repository.add.assert_awaited_once()

        with self.assertRaises(InvalidTenantLocaleError):
            await handler.execute(AddTenantLocaleCommand("invalid", actor))
        repository.add.assert_awaited_once()

    async def test_remove_only_selected_locale(self):
        repository = Mock(remove=AsyncMock(return_value=True))
        handler = RemoveTenantLocaleHandler(repository)
        await handler.execute(RemoveTenantLocaleCommand("en"))
        repository.remove.assert_awaited_once_with(TenantLocaleCodeVO("en"))
        repository.remove.return_value = False
        with self.assertRaises(TenantLocaleNotSelectedError):
            await handler.execute(RemoveTenantLocaleCommand("en"))

    async def test_system_list_is_stable(self):
        result = await ListSystemLocalesHandler().execute(ListSystemLocalesQuery())
        self.assertEqual([item.code for item in result], ["uk", "en"])

    async def test_public_selected_locale_check_validates_code(self):
        repository = Mock(contains=AsyncMock(return_value=True))
        handler = IsTenantLocaleSelectedHandler(repository)
        self.assertTrue(
            (await handler.execute(IsTenantLocaleSelectedQuery("uk"))).selected
        )
        repository.contains.assert_awaited_once_with(TenantLocaleCodeVO("uk"))
        with self.assertRaises(InvalidTenantLocaleError):
            await handler.execute(IsTenantLocaleSelectedQuery("invalid"))
        repository.contains.assert_awaited_once()
