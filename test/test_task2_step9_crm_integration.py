from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.crm.application import (
    CreateCompanyCommand,
    CreateCompanyUseCase,
    CreateContactCommand,
    CreateContactUseCase,
    GetCompanyQuery,
    GetCompanyUseCase,
    GetContactQuery,
    GetContactUseCase,
    UpdateCompanyCommand,
    UpdateCompanyUseCase,
    UpdateContactCommand,
    UpdateContactUseCase,
)
from src.modules.crm.infrastructure import (
    SqlAlchemyCompanyRepository,
    SqlAlchemyContactRepository,
)
from src.modules.shared.db.base import Base
from src.modules.shared.db.uow import UnitOfWork


class TestCrmIntegrationStep9(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step9_crm.sqlite3"

        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            future=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(
                text(
                    "CREATE TABLE contacts ("
                    "id CHAR(36) PRIMARY KEY, "
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "last_name VARCHAR(255) NOT NULL, "
                    "first_name VARCHAR(255) NOT NULL, "
                    "middle_name VARCHAR(255)"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE companies ("
                    "id CHAR(36) PRIMARY KEY, "
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "last_name VARCHAR(255) NOT NULL, "
                    "company_name VARCHAR(255) NOT NULL"
                    ")"
                )
            )

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_contact_core_create_update_get(self) -> None:
        uow = UnitOfWork(self._session_factory)
        async with uow:
            repository = SqlAlchemyContactRepository(uow.session)
            create_use_case = CreateContactUseCase(
                uow=uow,
                contact_repository=repository,
            )
            created = await create_use_case.execute(
                CreateContactCommand(
                    last_name="  Doe ",
                    first_name=" John ",
                    middle_name=" A ",
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            repository = SqlAlchemyContactRepository(uow.session)
            update_use_case = UpdateContactUseCase(
                uow=uow,
                contact_repository=repository,
            )
            updated = await update_use_case.execute(
                UpdateContactCommand(
                    contact_id=created.id,
                    last_name=" Roe ",
                    first_name=" Jane ",
                    middle_name=None,
                )
            )

        async with self._session_factory() as session:
            repository = SqlAlchemyContactRepository(session)
            get_use_case = GetContactUseCase(contact_repository=repository)
            fetched = await get_use_case.execute(GetContactQuery(contact_id=created.id))

        self.assertEqual(created.last_name, "Doe")
        self.assertEqual(created.first_name, "John")
        self.assertEqual(created.middle_name, "A")

        self.assertEqual(updated.last_name, "Roe")
        self.assertEqual(updated.first_name, "Jane")
        self.assertIsNone(updated.middle_name)
        self.assertGreaterEqual(updated.updated_at, created.updated_at)

        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.last_name, "Roe")
        self.assertEqual(fetched.first_name, "Jane")
        self.assertIsNone(fetched.middle_name)

    async def test_company_core_create_update_get(self) -> None:
        uow = UnitOfWork(self._session_factory)
        async with uow:
            repository = SqlAlchemyCompanyRepository(uow.session)
            create_use_case = CreateCompanyUseCase(
                uow=uow,
                company_repository=repository,
            )
            created = await create_use_case.execute(
                CreateCompanyCommand(
                    last_name=" Owner ",
                    company_name="  Acme ",
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            repository = SqlAlchemyCompanyRepository(uow.session)
            update_use_case = UpdateCompanyUseCase(
                uow=uow,
                company_repository=repository,
            )
            updated = await update_use_case.execute(
                UpdateCompanyCommand(
                    company_id=created.id,
                    last_name=" Director ",
                    company_name=" Acme Corp ",
                )
            )

        async with self._session_factory() as session:
            repository = SqlAlchemyCompanyRepository(session)
            get_use_case = GetCompanyUseCase(company_repository=repository)
            fetched = await get_use_case.execute(GetCompanyQuery(company_id=created.id))

        self.assertEqual(created.last_name, "Owner")
        self.assertEqual(created.company_name, "Acme")

        self.assertEqual(updated.last_name, "Director")
        self.assertEqual(updated.company_name, "Acme Corp")
        self.assertGreaterEqual(updated.updated_at, created.updated_at)

        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.last_name, "Director")
        self.assertEqual(fetched.company_name, "Acme Corp")


if __name__ == "__main__":
    unittest.main()
