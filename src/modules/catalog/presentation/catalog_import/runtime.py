from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import BinaryIO
from tempfile import SpooledTemporaryFile
from uuid import UUID
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.files.infrastructure.assembly import (
    build_artifact_files_facade,
    get_storage_resolver,
)
from src.modules.files.application.port.storage import StorageUnavailableError
from src.modules.files.domain.error import FileNotFoundError, InvalidFileError


class CatalogImportRuntime:
    """Внешняя сборка коротких UoW и сетевых фаз работы с Files."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], tenant_id: UUID
    ) -> None:
        """Принимает worker factory и доверенный tenant из envelope."""
        self.sessions, self.tenant_id = sessions, tenant_id

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[UnitOfWork]:
        """Открывает отдельный tenant UoW только на время SQL-фазы."""
        async with TenantGate(self.sessions).hold(self.tenant_id) as connection:
            await bind_tenant_schema(
                connection, self.tenant_id, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
            )
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                yield uow

    async def put(
        self,
        identifier: UUID,
        source: BinaryIO,
        size: int,
        name: str,
        content_type: str,
    ) -> None:
        """Резервирует Files ID, выполняет storage.put вне SQL и подтверждает запись."""
        async with self.transaction() as uow:
            facade = build_artifact_files_facade(uow.session)
            try:
                ready = await facade.location(self.tenant_id, identifier)
            except FileNotFoundError:
                ready = None
            if ready:
                if (ready.name, ready.content_type, ready.size_bytes) != (
                    name,
                    content_type,
                    size,
                ):
                    raise InvalidFileError("Artifact identity changed.")
                return
            location = await facade.reserve(
                self.tenant_id, identifier, name, content_type, size, datetime.now(UTC)
            )
        source.seek(0)
        actual = (
            await get_storage_resolver()
            .resolve(location.location)
            .put(location.location, location.key, source, size, content_type)
        )
        if actual != size:
            raise StorageUnavailableError("Artifact size mismatch.")
        async with self.transaction() as uow:
            await build_artifact_files_facade(uow.session).confirm(identifier, actual)

    async def open(self, identifier: UUID, limit: int) -> BinaryIO:
        """Открывает приватный снимок вне SQL и ограничивает фактическое чтение."""
        async with self.transaction() as uow:
            location = await build_artifact_files_facade(uow.session).location(
                self.tenant_id, identifier
            )
        stream = (
            await get_storage_resolver()
            .resolve(location.location)
            .open(location.location, location.key)
        )
        spool = SpooledTemporaryFile(max_size=1024 * 1024)
        received = 0
        try:
            async for chunk in stream:
                received += len(chunk)
                if received > limit:
                    raise StorageUnavailableError("Artifact limit exceeded.")
                spool.write(chunk)
            if received != location.size_bytes:
                raise StorageUnavailableError("Artifact size mismatch.")
            spool.seek(0)
            return spool
        except BaseException:
            spool.close()
            raise
        finally:
            await stream.aclose()
