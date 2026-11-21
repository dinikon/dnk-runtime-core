"""Редактирование PackagingType через Domain и write-порт без HTTP и PostgreSQL."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from src.modules.inventory.application.packaging_type.command.update_packaging_type.command import (
    UpdatePackagingTypeCommand,
)
from src.modules.inventory.application.packaging_type.command.update_packaging_type.handler import (
    UpdatePackagingTypeHandler,
)
from src.modules.inventory.domain.error import InvalidPackagingValueError
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeNotFoundError,
    PackagingTypeCodeAlreadyExistsError,
)
from src.modules.inventory.domain.packaging_type.repository import (
    PackagingTypeRepositoryProtocol,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.infrastructure.packaging_type.persistence.repository import (
    SqlAlchemyPackagingTypeRepository,
)
from test.test_inventory_packaging_type_application import DriverConstraintError


class PackagingTypeMutationsApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет присутствие полей, immutable Domain и пропуск нормализованного no-op."""

    async def asyncSetUp(self) -> None:
        """Готовит активный тип и наблюдаемый порт текущей транзакции."""
        self.kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("BOX"),
            name=PackagingNameVO("Ящик"),
        )
        self.repository = Mock(spec=PackagingTypeRepositoryProtocol)
        self.repository.get_for_update = AsyncMock(return_value=self.kind)
        self.repository.save = AsyncMock()
        self.handler = UpdatePackagingTypeHandler(self.repository)
        self.command = UpdatePackagingTypeCommand(
            self.kind.id, frozenset({"is_active"}), is_active=False
        )

    async def test_explicit_false_preserves_omitted_values_identity_and_source(
        self,
    ) -> None:
        """Деактивация меняет только собственную активность и сохраняет исходный объект."""
        result = await self.handler.execute(self.command)
        self.assertEqual(
            (result.id, result.code, result.name, result.is_active),
            (self.kind.id.uuid, "BOX", "Ящик", False),
        )
        self.repository.get_for_update.assert_awaited_once_with(self.kind.id)
        self.repository.save.assert_awaited_once_with(self.kind.deactivate())
        self.assertTrue(self.kind.is_active)

    async def test_full_update_and_inactive_edit_use_domain_normalization(self) -> None:
        """Редактирует неактивный тип и явно активирует его без изменения UUID."""
        self.repository.get_for_update.return_value = self.kind.deactivate()
        result = await self.handler.execute(
            replace(
                self.command,
                fields=frozenset({"code", "name", "is_active"}),
                code=" PALLET ",
                name=" Палета ",
                is_active=True,
            )
        )
        self.assertEqual(
            (result.code, result.name, result.is_active), ("PALLET", "Палета", True)
        )
        self.assertEqual(result.id, self.kind.id.uuid)
        result = await self.handler.execute(
            replace(self.command, fields=frozenset({"name"}), name="Новое название")
        )
        self.assertEqual(result.name, "Новое название")
        self.assertFalse(result.is_active)

    async def test_normalized_noop_and_repeated_activity_do_not_write(self) -> None:
        """Повторные команды и trim-эквивалентное представление не вызывают save."""
        await self.handler.execute(
            replace(
                self.command,
                fields=frozenset({"code", "name", "is_active"}),
                code=" BOX ",
                name=" Ящик ",
                is_active=True,
            )
        )
        self.repository.get_for_update.return_value = self.kind.deactivate()
        await self.handler.execute(self.command)
        self.repository.save.assert_not_awaited()

    async def test_case_change_is_a_real_update(self) -> None:
        """Код сохраняет регистр: переход BOX в box не считается no-op."""
        result = await self.handler.execute(
            replace(self.command, fields=frozenset({"code"}), code="box")
        )
        self.assertEqual(result.code, "box")
        self.repository.save.assert_awaited_once_with(
            self.kind.change_code(PackagingCodeVO("box"))
        )

    async def test_domain_rejection_or_missing_record_never_saves(self) -> None:
        """Неверное имя не сохраняет уже подготовленный код, отсутствие не создаёт запись."""
        for code, name in ((" ", "Name"), ("NEW", "Bad\u200bName")):
            with (
                self.subTest(code=code, name=name),
                self.assertRaises(InvalidPackagingValueError),
            ):
                await self.handler.execute(
                    replace(
                        self.command,
                        fields=frozenset({"code", "name"}),
                        code=code,
                        name=name,
                    )
                )
        self.repository.get_for_update.return_value = None
        with self.assertRaises(PackagingTypeNotFoundError):
            await self.handler.execute(self.command)
        self.repository.save.assert_not_awaited()
        self.assertEqual(self.kind.code.value, "BOX")

    async def test_write_failure_propagates_to_external_uow(self) -> None:
        """Конфликт и технический отказ не превращаются в успешный результат."""
        for cause in (
            PackagingTypeCodeAlreadyExistsError("occupied"),
            RuntimeError("write failed"),
        ):
            self.repository.save.side_effect = cause
            with (
                self.subTest(cause=type(cause).__name__),
                self.assertRaises(type(cause)),
            ):
                await self.handler.execute(self.command)
        self.assertTrue(self.kind.is_active)

    async def test_repository_update_missing_does_not_upsert(self) -> None:
        """RETURNING без строки преобразуется в предметное отсутствие типа тары."""
        session = Mock(scalar=AsyncMock(return_value=None))
        with self.assertRaises(PackagingTypeNotFoundError):
            await SqlAlchemyPackagingTypeRepository(session).save(self.kind)
        session.scalar.assert_awaited_once()

    async def test_repository_update_translates_only_known_unique(self) -> None:
        """UPDATE сохраняет причину известного конфликта и пробрасывает неизвестные ошибки."""
        for constraint, expected in (
            ("uq_packaging_types_code", PackagingTypeCodeAlreadyExistsError),
            ("unknown", IntegrityError),
        ):
            error = IntegrityError(
                "UPDATE", {}, DriverConstraintError("23505", constraint)
            )
            repository = SqlAlchemyPackagingTypeRepository(
                Mock(scalar=AsyncMock(side_effect=error))
            )
            with (
                self.subTest(constraint=constraint),
                self.assertRaises(expected) as caught,
            ):
                await repository.save(self.kind)
            self.assertIs(
                (
                    caught.exception
                    if expected is IntegrityError
                    else caught.exception.__cause__
                ),
                error,
            )
