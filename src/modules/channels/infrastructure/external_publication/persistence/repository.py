from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.external_publication.persistence.mapper import (
    ExternalPublicationMapper,
)


class SqlAlchemyExternalPublicationRepository:
    """Сохраняет наблюдения под сериализацией run/Channel без Catalog writes."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию текущего tenant UoW."""
        self.session = session

    async def find(
        self, connection_id: EntityIdVO, resource_type: str, external_id: str
    ) -> ExternalPublication | None:
        """Загружает наблюдение по подтверждённой составной identity."""
        row = (
            (
                await self.session.execute(
                    select(ExternalPublicationModel.__table__).where(
                        ExternalPublicationModel.connection_id == connection_id.uuid,
                        ExternalPublicationModel.resource_type == resource_type,
                        ExternalPublicationModel.external_id == external_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else ExternalPublicationMapper.to_domain(row)

    async def add(self, publication: ExternalPublication) -> None:
        """Добавляет новую identity без commit."""
        await self.session.execute(
            insert(ExternalPublicationModel).values(
                **ExternalPublicationMapper.to_values(publication)
            )
        )

    async def save(self, publication: ExternalPublication) -> None:
        """Обновляет существующее наблюдение без commit."""
        await self.session.execute(
            update(ExternalPublicationModel)
            .where(ExternalPublicationModel.id == publication.id.uuid)
            .values(**ExternalPublicationMapper.to_values(publication))
        )
