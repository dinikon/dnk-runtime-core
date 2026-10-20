from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.product_representation.contracts import (
    PublicationCatalogSourceDTO,
)
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel as C,
)
from src.modules.channels.infrastructure.persistence.models.channel import (
    ChannelModel as H,
)


class SqlAlchemyPublicationCatalogSource:
    """Читает observed snapshot и admission локальной команды связи."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует общую tenant-сессию без собственного UoW."""
        self.session = session

    async def source(
        self, publication_id: UUID, *, lock: bool = False
    ) -> PublicationCatalogSourceDTO:
        """При записи блокирует Channel SHARE, затем публикацию FOR UPDATE."""
        channel_id = await self.session.scalar(
            select(C.channel_id)
            .join(P, P.connection_id == C.id)
            .where(P.id == publication_id)
        )
        if channel_id is None:
            raise ChannelsNotFoundError("publication_not_found")
        statement = select(H.is_archived).where(H.id == channel_id)
        if lock:
            statement = statement.with_for_update(read=True)
        archived = await self.session.scalar(statement)
        statement = select(P.__table__).where(P.id == publication_id)
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).mappings().one()
        payload = PublicationPayloadVO.from_document(row["payload"])
        return PublicationCatalogSourceDTO(
            row["id"],
            row["connection_id"],
            channel_id,
            bool(archived),
            row["observed_revision"],
            payload.title,
            payload.display_locale,
            payload.sku,
            payload.price,
            payload.sale_price,
            payload.currency,
            payload.quantity,
            payload.stock_status,
            tuple(row["meta"]["read_issues"]),
            payload.main_image_url,
            row["resource_type"],
            row["external_id"],
            dict(row["meta"]["provider"]),
        )
