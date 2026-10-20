from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from sqlalchemy import select, insert, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.publication_import.aggregate import (
    PublicationImportPreparation,
)
from src.modules.channels.infrastructure.persistence.models.publication_import import (
    PublicationImportModel as M,
)
from src.modules.channels.infrastructure.publication_import.persistence.mapper import (
    PublicationImportMapper,
)
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemyPublicationImportRepository:
    """Сохраняет самостоятельный процесс на сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает уже привязанную tenant-сессию."""
        self.session = session

    async def lock_request(self, tenant_id: EntityIdVO, identifier: EntityIdVO) -> None:
        """Сериализует повтор запуска до появления строки подготовки."""
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": str(tenant_id.uuid) + ":channel-import:" + str(identifier.uuid)},
        )

    async def get(
        self, identifier: EntityIdVO, *, lock: bool = True
    ) -> PublicationImportPreparation:
        """Восстанавливает только write-процесс, при изменениях берёт FOR UPDATE."""
        statement = select(M.__table__).where(M.id == identifier.uuid)
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).mappings().one_or_none()
        if row is None:
            raise ChannelsNotFoundError("import_preparation_not_found")
        return PublicationImportMapper.to_domain(row)

    async def add(self, preparation: PublicationImportPreparation) -> None:
        """Вставляет процесс без commit."""
        await self.session.execute(
            insert(M).values(**PublicationImportMapper.to_values(preparation))
        )

    async def save(self, preparation: PublicationImportPreparation) -> None:
        """Сохраняет доменный переход на общей сессии."""
        values = PublicationImportMapper.to_values(preparation)
        values.pop("id")
        await self.session.execute(
            update(M).where(M.id == preparation.id.uuid).values(**values)
        )
