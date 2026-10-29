from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.channel import (
    ChannelModel as C,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel as N,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationCreationSnapshot,
    PublicationLookup,
)
from src.modules.channels.application.external_publication.catalog_creation_error import (
    PublicationCatalogError,
)
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)


class SqlAlchemyPublicationCreationRead:
    """Читает контекст операции без ORM наружу и восстановления агрегатов."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает внешнюю tenant сессию."""
        self.session = session

    async def snapshot(
        self, channel_id: UUID, publication_id: UUID
    ) -> PublicationCreationSnapshot:
        """Разрешает выбранную разновидность в корень и читает всю локальную семью."""
        connection = (
            (
                await self.session.execute(
                    select(N.__table__, C.platform_kind)
                    .join(C, C.id == N.channel_id)
                    .where(C.id == channel_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if connection is None:
            raise PublicationCatalogError("channel_not_found")
        selected = (
            await self.session.execute(
                select(P.id, P.parent_id).where(
                    P.id == publication_id, P.connection_id == connection["id"]
                )
            )
        ).one_or_none()
        if selected is None:
            raise PublicationCatalogError("publication_not_found")
        root = selected.parent_id or selected.id
        rows = (
            await self.session.execute(
                select(
                    P.id,
                    P.resource_type,
                    P.external_id,
                    P.kind,
                    P.parent_id,
                    P.revision,
                    P.platform_data,
                )
                .where(
                    P.connection_id == connection["id"],
                    or_(P.id == root, P.parent_id == root),
                )
                .order_by(P.id)
            )
        ).all()
        return PublicationCreationSnapshot(
            connection["id"],
            connection["platform_kind"],
            ConnectionConfigVO.create(
                version=connection["config_version"],
                endpoint=connection["endpoint"],
                settings=connection["settings"],
            ),
            connection["config_revision"],
            connection["encrypted_credentials"],
            root,
            tuple(
                PublicationLookup(
                    r.id,
                    r.resource_type,
                    r.external_id,
                    r.kind,
                    r.parent_id,
                    r.revision,
                    r.platform_data,
                )
                for r in rows
            ),
        )
