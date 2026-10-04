"""Domain, application и публичная ссылка Inventory.SKU."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.inventory.domain.sku.aggregate import Sku
from src.modules.inventory.domain.sku.error import (
    InvalidSkuCodeError,
    InvalidSkuTitleError,
    SkuNotFoundError,
)
from src.modules.inventory.domain.sku.value_object.code import SkuCodeVO
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO
from src.modules.inventory.domain.warehouse.value_object.warehouse_id import (
    WarehouseIdVO,
)
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.inventory.application.sku.command.create_sku.command import (
    CreateSkuCommand,
)
from src.modules.inventory.application.sku.command.create_sku.handler import (
    CreateSkuHandler,
)
from src.modules.inventory.application.sku.query.get_sku.dto import SkuDetailsDTO
from src.modules.inventory.application.sku.query.get_sku.handler import GetSkuHandler
from src.modules.inventory.application.sku.query.get_sku.query import GetSkuQuery
from src.modules.inventory.application.sku.query.list_skus.query import ListSkusQuery
from src.modules.inventory.application.sku.query.list_skus.handler import (
    ListSkusHandler,
)


class SkuDomainTests(unittest.TestCase):
    def make(self, **changes):
        args = dict(
            sku_id=SkuIdVO(uuid4()),
            code=" OMEGA-100 ",
            title=" Omega 100 ",
            actor_id=EntityIdVO(uuid4()),
            now=datetime(2026, 10, 4, tzinfo=UTC),
        )
        args.update(changes)
        return Sku.create(**args)

    def test_create_normalizes_without_changing_code_case_and_preserves_audit(self):
        sku = self.make(code="  Omega-100  ")
        self.assertEqual(sku.code.value, "Omega-100")
        self.assertEqual(sku.title.value, "Omega 100")
        self.assertEqual(sku.created_at, sku.updated_at)
        self.assertEqual(sku.created_by, sku.updated_by)
        self.assertNotEqual(SkuCodeVO("A"), SkuCodeVO("a"))
        with self.assertRaises(FrozenInstanceError):
            sku.code.value = "other"

    def test_invalid_codes_and_titles_are_rejected(self):
        for code in (
            None,
            False,
            123,
            [],
            "",
            " ",
            "a" * 129,
            "a\nb",
            "a\tb",
            "a\x00b",
            "a\x7fb",
        ):
            with self.subTest(code=code), self.assertRaises(InvalidSkuCodeError):
                self.make(code=code)
        for title in (None, False, 123, "", " ", "a" * 256):
            with self.subTest(title=title), self.assertRaises(InvalidSkuTitleError):
                self.make(title=title)
        self.assertEqual(
            len(self.make(code="a" * 128, title="a" * 255).code.value), 128
        )

    def test_wrong_identifier_types_cannot_be_used_for_sku(self):
        for value in (uuid4(), EntityIdVO(uuid4()), WarehouseIdVO(uuid4())):
            with self.subTest(value=value), self.assertRaises(EntityIdTypeError):
                self.make(sku_id=value)
        with self.assertRaises(EntityIdTypeError):
            self.make(actor_id=uuid4())
        with self.assertRaises(EntityIdTypeError):
            SkuIdVO.from_value(WarehouseIdVO(uuid4()))


class SkuApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_command_never_writes_and_storage_errors_propagate(self):
        repository = Mock(add=AsyncMock())
        handler = CreateSkuHandler(
            repository,
            Mock(now=Mock(return_value=datetime.now(UTC))),
            Mock(new=Mock(return_value=uuid4())),
        )
        command = CreateSkuCommand(EntityIdVO(uuid4()), " ", "Title")
        with self.assertRaises(InvalidSkuCodeError):
            await handler.execute(command)
        repository.add.assert_not_awaited()
        repository.add.side_effect = RuntimeError("storage")
        with self.assertRaises(RuntimeError):
            await handler.execute(replace(command, code="A"))

    async def test_read_scenarios_use_projection_without_aggregate(self):
        identifier, actor, now = uuid4(), uuid4(), datetime.now(UTC)
        details = SkuDetailsDTO(identifier, "A", "Title", now, now, actor, actor)
        repository = Mock(
            get_details=AsyncMock(return_value=details),
            list_details=AsyncMock(return_value=[details]),
        )
        result = await ListSkusHandler(repository).execute(
            ListSkusQuery(limit=5, offset=10)
        )
        repository.list_details.assert_awaited_once_with(limit=5, offset=10)
        self.assertEqual(result.skus, (details,))
        repository.get_details.return_value = None
        with self.assertRaises(SkuNotFoundError):
            await GetSkuHandler(repository).execute(GetSkuQuery(SkuIdVO(identifier)))
        repository.get_details.assert_awaited_once_with(sku_id=SkuIdVO(identifier))

    async def test_query_limits_are_validated_for_non_http_consumers(self):
        repository = Mock(list_details=AsyncMock())
        handler = ListSkusHandler(repository)
        for args in (
            dict(limit=0),
            dict(limit=201),
            dict(limit=True),
            dict(limit="5"),
            dict(offset=-1),
            dict(offset=True),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                await handler.execute(ListSkusQuery(**args))
        repository.list_details.assert_not_awaited()
