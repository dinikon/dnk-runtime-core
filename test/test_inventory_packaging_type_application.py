"""Сценарии типов тары и перевод известных ошибок хранения без PostgreSQL."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from src.modules.inventory.application.packaging_type.command.create_packaging_type.command import (
    CreatePackagingTypeCommand,
)
from src.modules.inventory.application.packaging_type.command.create_packaging_type.handler import (
    CreatePackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.query import (
    GetPackagingTypeQuery,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.dto import (
    GetPackagingTypeResultDTO,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.handler import (
    GetPackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.query import (
    ListPackagingTypesQuery,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.dto import (
    ListPackagingTypesResultDTO,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.handler import (
    ListPackagingTypesHandler,
)
from src.modules.inventory.domain.error import InvalidPackagingValueError
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeCodeAlreadyExistsError,
    PackagingTypeNotFoundError,
)
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.infrastructure.packaging_type.persistence.repository import (
    SqlAlchemyPackagingTypeRepository,
)


class DriverConstraintError(Exception):
    """Передаёт типизированные метаданные известного или неизвестного ограничения."""

    def __init__(self, sqlstate: str, constraint_name: str) -> None:
        """Сохраняет данные драйвера без зависимости теста от asyncpg."""
        super().__init__("constraint failure")
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


class PackagingTypeApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет Domain-фабрику, конкретные DTO и независимость чтения от агрегата."""

    async def test_create_preserves_case_and_uses_domain_defaults(self) -> None:
        """Убирает пробелы, сохраняет регистр и назначает активность на стороне Domain."""
        identifier = uuid4()
        repository = Mock(add=AsyncMock())
        generator = Mock(new=Mock(return_value=identifier))
        result = await CreatePackagingTypeHandler(repository, generator).execute(
            CreatePackagingTypeCommand(" BOX ", " Ящик ")
        )
        self.assertEqual(
            (result.id, result.code, result.name, result.is_active),
            (identifier, "BOX", "Ящик", True),
        )
        saved = repository.add.await_args.args[0]
        self.assertIsInstance(saved, PackagingType)
        self.assertEqual(saved.id, PackagingTypeIdVO(identifier))
        generator.new.assert_called_once_with()
        repository.add.assert_awaited_once()

    async def test_invalid_values_do_not_write(self) -> None:
        """Проверки значений выполняет Domain, не допуская частичной записи."""
        repository = Mock(add=AsyncMock())
        handler = CreatePackagingTypeHandler(
            repository, Mock(new=Mock(side_effect=uuid4))
        )
        for code, name in (
            (" ", "Name"),
            ("BOX", ""),
            ("B\u200bOX", "Name"),
            ("BOX", "Bad\nName"),
        ):
            with (
                self.subTest(code=code, name=name),
                self.assertRaises(InvalidPackagingValueError),
            ):
                await handler.execute(CreatePackagingTypeCommand(code, name))
        repository.add.assert_not_awaited()

    async def test_create_propagates_known_conflict_and_technical_failure(self) -> None:
        """Ошибка порта не превращается в результат создания до внешнего UoW."""
        for error in (
            PackagingTypeCodeAlreadyExistsError("occupied"),
            RuntimeError("write failed"),
        ):
            repository = Mock(add=AsyncMock(side_effect=error))
            with (
                self.subTest(error=type(error).__name__),
                self.assertRaises(type(error)),
            ):
                await CreatePackagingTypeHandler(
                    repository, Mock(new=Mock(side_effect=uuid4))
                ).execute(CreatePackagingTypeCommand("BOX", "Ящик"))

    async def test_get_returns_projection_or_not_found(self) -> None:
        """Карточка читается через порт DTO без загрузки Domain."""
        query = GetPackagingTypeQuery(PackagingTypeIdVO(uuid4()))
        dto = GetPackagingTypeResultDTO(
            query.packaging_type_id.uuid, "BOX", "Ящик", False
        )
        repository = Mock(get_details=AsyncMock(return_value=dto))
        self.assertIs(await GetPackagingTypeHandler(repository).execute(query), dto)
        repository.get_details.assert_awaited_once_with(query)
        repository.get_details.return_value = None
        with self.assertRaises(PackagingTypeNotFoundError):
            await GetPackagingTypeHandler(repository).execute(query)

    async def test_list_normalizes_only_search_and_preserves_false(self) -> None:
        """Trim поиска не подменяет регистр кода и не теряет false и пагинацию."""
        dto = ListPackagingTypesResultDTO((), 0, 20, 20)
        repository = Mock(list=AsyncMock(return_value=dto))
        handler = ListPackagingTypesHandler(repository)
        query = ListPackagingTypesQuery(
            offset=20, limit=20, search="  ЯЩИК%_ ", is_active=False
        )
        self.assertIs(await handler.execute(query), dto)
        repository.list.assert_awaited_once_with(replace(query, search="ЯЩИК%_"))
        await handler.execute(replace(query, search="  "))
        self.assertIsNone(repository.list.await_args.args[0].search)

    async def test_repository_translates_only_exact_unique_and_keeps_cause(
        self,
    ) -> None:
        """Известный UNIQUE распознаётся и в обёрнутой причине драйвера."""
        packaging_type = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("BOX"),
            name=PackagingNameVO("Ящик"),
        )
        for state, constraint, expected in (
            ("23505", "uq_packaging_types_code", PackagingTypeCodeAlreadyExistsError),
            ("23503", "uq_packaging_types_code", IntegrityError),
            ("23505", "other_constraint", IntegrityError),
        ):
            for nested in (False, True):
                driver = DriverConstraintError(state, constraint)
                original = Exception("wrapper") if nested else driver
                if nested:
                    original.__cause__ = driver
                error = IntegrityError("INSERT", {}, original)
                repository = SqlAlchemyPackagingTypeRepository(
                    Mock(execute=AsyncMock(side_effect=error))
                )
                with (
                    self.subTest(state=state, constraint=constraint, nested=nested),
                    self.assertRaises(expected) as caught,
                ):
                    await repository.add(packaging_type)
                self.assertIs(
                    (
                        caught.exception
                        if expected is IntegrityError
                        else caught.exception.__cause__
                    ),
                    error,
                )
        error = IntegrityError("INSERT", {}, None)
        with self.assertRaises(IntegrityError) as caught:
            await SqlAlchemyPackagingTypeRepository(
                Mock(execute=AsyncMock(side_effect=error))
            ).add(packaging_type)
        self.assertIs(caught.exception, error)
