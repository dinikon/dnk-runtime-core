"""Доменный запрет удаления типа тары, порядок сценария и защитный перевод FK."""

import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.dml import Delete

from src.modules.inventory.application.packaging_type.command.delete_packaging_type.command import (
    DeletePackagingTypeCommand,
)
from src.modules.inventory.application.packaging_type.command.delete_packaging_type.handler import (
    DeletePackagingTypeHandler,
)
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.deletion_usage import (
    PackagingTypeDeletionUsage,
)
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeInUseError,
    PackagingTypeNotFoundError,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.infrastructure.packaging_type.persistence.repository import (
    SqlAlchemyPackagingTypeRepository,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.usage import (
    SqlAlchemyPackagingTypeUsage,
)
from test.test_inventory_packaging_type_application import DriverConstraintError


class PackagingTypeDeleteApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет правило независимо от активности и отказ до попытки SQL DELETE."""

    async def asyncSetUp(self) -> None:
        """Готовит агрегат и наблюдаемые порты одного внешнего процесса."""
        self.kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("BOX"),
            name=PackagingNameVO("Ящик"),
        )
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.kind), delete=AsyncMock()
        )
        self.usage = Mock(get=AsyncMock(return_value=PackagingTypeDeletionUsage(False)))
        self.handler = DeletePackagingTypeHandler(self.repository, self.usage)
        self.command = DeletePackagingTypeCommand(self.kind.id)

    async def test_domain_rule_is_independent_of_activity(self) -> None:
        """Любой используемый тип защищён; неиспользуемый удаляется в обоих состояниях."""
        for kind in (self.kind, self.kind.deactivate()):
            with self.subTest(active=kind.is_active):
                self.assertIsNone(
                    kind.ensure_can_delete(PackagingTypeDeletionUsage(False))
                )
                with self.assertRaises(PackagingTypeInUseError):
                    kind.ensure_can_delete(PackagingTypeDeletionUsage(True))
        self.assertTrue(self.kind.is_active)
        self.assertFalse(self.kind.deactivate().is_active)

    async def test_unused_root_is_locked_checked_then_deleted_without_result(
        self,
    ) -> None:
        """Оба порта используют ID корня, загрузка предшествует проверке и удалению."""
        calls = Mock()
        calls.attach_mock(self.repository.get_for_update, "lock")
        calls.attach_mock(self.usage.get, "usage")
        calls.attach_mock(self.repository.delete, "delete")
        for kind in (self.kind, self.kind.deactivate()):
            calls.reset_mock()
            self.repository.get_for_update.return_value = kind
            self.assertIsNone(await self.handler.execute(self.command))
            self.assertEqual(
                [call[0] for call in calls.mock_calls], ["lock", "usage", "delete"]
            )
            self.repository.get_for_update.assert_awaited_once_with(kind.id)
            self.usage.get.assert_awaited_once_with(kind.id)
            self.repository.delete.assert_awaited_once_with(kind)

    async def test_used_root_never_reaches_delete(self) -> None:
        """Бизнес-отказ возникает до удаления даже у неактивного типа."""
        self.usage.get.return_value = PackagingTypeDeletionUsage(True)
        for kind in (self.kind, self.kind.deactivate()):
            self.repository.get_for_update.return_value = kind
            with self.assertRaises(PackagingTypeInUseError):
                await self.handler.execute(self.command)
        self.repository.delete.assert_not_awaited()

    async def test_missing_root_does_not_query_usage_or_delete(self) -> None:
        """Отсутствие различается до обращения к ссылкам и не считается успешным повтором."""
        self.repository.get_for_update.return_value = None
        with self.assertRaises(PackagingTypeNotFoundError):
            await self.handler.execute(self.command)
        self.usage.get.assert_not_awaited()
        self.repository.delete.assert_not_awaited()

    async def test_read_or_write_failures_propagate_to_external_uow(self) -> None:
        """Непредвиденный отказ порта не скрывается успешным завершением команды."""
        self.usage.get.side_effect = RuntimeError("usage unavailable")
        with self.assertRaisesRegex(RuntimeError, "usage unavailable"):
            await self.handler.execute(self.command)
        self.repository.delete.assert_not_awaited()
        self.usage.get.side_effect = None
        self.repository.delete.side_effect = RuntimeError("write unavailable")
        with self.assertRaisesRegex(RuntimeError, "write unavailable"):
            await self.handler.execute(self.command)

    async def test_usage_is_a_single_exists_by_type_id(self) -> None:
        """EXISTS не восстанавливает агрегаты и не блокирует InventoryItem."""
        for used in (False, True):
            session = Mock(
                execute=AsyncMock(return_value=Mock(scalar_one=Mock(return_value=used)))
            )
            result = await SqlAlchemyPackagingTypeUsage(session).get(self.kind.id)
            self.assertEqual(result, PackagingTypeDeletionUsage(used))
            statement = session.execute.await_args.args[0]
            self.assertIn("EXISTS", str(statement))
            self.assertNotIn("FOR UPDATE", str(statement))
            self.assertIn(self.kind.id.uuid, statement.compile().params.values())
            session.commit.assert_not_called()
            session.rollback.assert_not_called()

    async def test_delete_uses_returning_and_does_not_commit(self) -> None:
        """Один типизированный DELETE различает отсутствие без дополнительного SELECT."""
        session = Mock(scalar=AsyncMock(return_value=self.kind.id.uuid))
        self.assertIsNone(
            await SqlAlchemyPackagingTypeRepository(session).delete(self.kind)
        )
        statement = session.scalar.await_args.args[0]
        self.assertIsInstance(statement, Delete)
        self.assertIn("RETURNING", str(statement))
        self.assertIn(self.kind.id.uuid, statement.compile().params.values())
        session.execute.assert_not_called()
        session.commit.assert_not_called()
        session.rollback.assert_not_called()
        session.scalar.return_value = None
        with self.assertRaises(PackagingTypeNotFoundError):
            await SqlAlchemyPackagingTypeRepository(session).delete(self.kind)

    async def test_delete_translates_only_the_known_fk_and_preserves_cause(
        self,
    ) -> None:
        """И SQLSTATE, и имя ограничения обязательны; метаданные могут лежать в cause."""
        for sqlstate in ("23503", "23001"):
            for wrapped in (False, True):
                driver = DriverConstraintError(sqlstate, "fk_item_packagings_type")
                original = Exception("dbapi wrapper") if wrapped else driver
                if wrapped:
                    original.__cause__ = driver
                error = IntegrityError("DELETE", {}, original)
                session = Mock(scalar=AsyncMock(side_effect=error))
                with self.assertRaises(PackagingTypeInUseError) as caught:
                    await SqlAlchemyPackagingTypeRepository(session).delete(self.kind)
                self.assertIs(caught.exception.__cause__, error)
                session.rollback.assert_not_called()
        without_original = IntegrityError("DELETE", {}, Exception("no original"))
        without_original.orig = None
        errors = [without_original] + [
            IntegrityError("DELETE", {}, original)
            for original in (
                Exception("no driver metadata"),
                DriverConstraintError("23503", "unrelated_fk"),
                DriverConstraintError("23001", "unrelated_fk"),
                DriverConstraintError("23505", "fk_item_packagings_type"),
            )
        ]
        for error in errors:
            session = Mock(scalar=AsyncMock(side_effect=error))
            with self.assertRaises(IntegrityError) as caught:
                await SqlAlchemyPackagingTypeRepository(session).delete(self.kind)
            self.assertIs(caught.exception, error)
