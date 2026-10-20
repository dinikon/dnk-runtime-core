from uuid import UUID
from sqlalchemy.sql.selectable import CTE
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.external_publication.identity_contract import (
    PublicationIdentityPolicyDTO,
)
from src.modules.channels.application.external_publication.query.list_external_publications.dto import (
    ListPublicationIdentitySummaryDTO,
)
from src.modules.channels.infrastructure.external_publication.persistence.identity_query import (
    publication_identity_projection,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from sqlalchemy import select, func, or_, and_, Text, literal_column
from src.modules.channels.infrastructure.persistence.models.external_binding import (
    ExternalBindingModel as B,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as R,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_mapper import (
    ExternalPublicationQueryMapper,
)
from src.modules.channels.application.external_publication.query.get_external_publication.query import (
    GetExternalPublicationQuery,
)
from src.modules.channels.application.external_publication.query.get_external_publication.dto import (
    GetExternalPublicationResultDTO,
)
from src.modules.channels.application.external_publication.query.list_external_publications.query import (
    ListExternalPublicationsQuery,
)
from src.modules.channels.application.external_publication.query.list_external_publications.dto import (
    ListExternalPublicationsResultDTO,
)
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemyExternalPublicationQueryRepository:
    """Читает только локальные публикации с фильтрами и tenant из внешнего UoW."""

    def __init__(self, session: AsyncSession, registry: PluginRegistryProtocol) -> None:
        """Не выполняет внешних запросов при открытии списка."""
        self.session, self.registry = session, registry

    async def get_external_publication(
        self, query: GetExternalPublicationQuery
    ) -> GetExternalPublicationResultDTO:
        """Читает одну detail projection либо возвращает предметный not found."""
        connection_id = await self.session.scalar(
            select(ExternalPublicationModel.connection_id).where(
                ExternalPublicationModel.id == query.publication_id
            )
        )
        if connection_id is None:
            raise ChannelsNotFoundError("publication_not_found")
        policy, _, _ = await self._scope(connection_id)
        identity = publication_identity_projection(connection_id, policy)
        table = ExternalPublicationModel.__table__
        row = (
            (
                await self.session.execute(
                    select(
                        table,
                        identity.c.identity_state,
                        identity.c.identity_key,
                        identity.c.identity_conflict_count,
                    )
                    .join(identity, identity.c.id == table.c.id)
                    .where(table.c.id == query.publication_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("publication_not_found")
        return ExternalPublicationQueryMapper.to_details(row)

    async def list_external_publications(
        self, query: ListExternalPublicationsQuery
    ) -> ListExternalPublicationsResultDTO:
        """Фильтрует JSONB в SQL и не загружает provider metadata для списка."""
        policy, generation, limitations = await self._scope(query.connection_id)
        identity = publication_identity_projection(query.connection_id, policy)
        summary = await self._identity_summary(
            query.connection_id, policy, identity, generation, limitations
        )
        table = ExternalPublicationModel.__table__
        conditions = [table.c.connection_id == query.connection_id]
        if query.search:
            escaped = (
                query.search.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            conditions.append(
                or_(
                    table.c.payload.op("->")("titles")
                    .op("->>", return_type=Text())(
                        func.coalesce(
                            table.c.payload.op("->>", return_type=Text())(
                                "display_locale"
                            ),
                            "und",
                        )
                    )
                    .ilike("%" + escaped + "%", escape="\\"),
                    table.c.payload.op("->>", return_type=Text())(
                        literal_column("'sku'")
                    ).ilike("%" + escaped + "%", escape="\\"),
                    table.c.external_id == query.search,
                )
            )
        if query.stock_status:
            conditions.append(
                table.c.payload.op("->")(literal_column("'stock'")).op(
                    "->>", return_type=Text()
                )(literal_column("'status'"))
                == query.stock_status
            )
        if query.identity_status:
            conditions.append(identity.c.identity_state == query.identity_status)
        if query.identity_key is not None:
            conditions.append(identity.c.identity_key == query.identity_key)
        joined = (
            table.join(identity, identity.c.id == table.c.id)
            .outerjoin(
                B.__table__,
                and_(B.publication_id == table.c.id, B.released_at.is_(None)),
            )
            .outerjoin(R.__table__, R.id == B.representation_id)
        )
        if query.binding_status == "bound":
            conditions.append(B.id.is_not(None))
        if query.binding_status == "unbound":
            conditions.append(B.id.is_(None))
        total = await self.session.scalar(
            select(func.count()).select_from(joined).where(*conditions)
        )
        columns = [
            column for column in table.c if column.name not in ("meta", "fingerprint")
        ]
        columns.append(table.c.meta.op("->")("read_issues").label("read_issues"))
        columns.extend(
            (
                identity.c.identity_state,
                identity.c.identity_key,
                identity.c.identity_conflict_count,
            )
        )
        columns.extend(
            (
                R.catalog_item_id.label("catalog_item_id"),
                B.id.label("binding_id"),
                R.id.label("representation_id"),
                R.revision.label("representation_revision"),
            )
        )
        rows = (
            (
                await self.session.execute(
                    select(*columns)
                    .select_from(joined)
                    .where(*conditions)
                    .order_by(table.c.id)
                    .offset(query.offset)
                    .limit(query.limit)
                )
            )
            .mappings()
            .all()
        )
        return ListExternalPublicationsResultDTO(
            tuple((ExternalPublicationQueryMapper.to_list_item(row) for row in rows)),
            total,
            summary,
        )

    async def _scope(
        self, connection_id: UUID
    ) -> tuple[PublicationIdentityPolicyDTO | None, int, tuple[str, ...]]:
        """Разрешает политику зарегистрированного плагина без чтения credentials."""
        row = (
            await self.session.execute(
                select(
                    ChannelModel.platform_kind,
                    ConnectionModel.generation,
                    ConnectionModel.scope_limitations,
                )
                .join(ConnectionModel, ConnectionModel.channel_id == ChannelModel.id)
                .where(ConnectionModel.id == connection_id)
            )
        ).one_or_none()
        if row is None:
            raise ChannelsNotFoundError("connection_not_found")
        return (
            self.registry.manifest(row.platform_kind).publication_identity,
            row.generation,
            tuple(row.scope_limitations),
        )

    async def _identity_summary(
        self,
        connection_id: UUID,
        policy: PublicationIdentityPolicyDTO | None,
        identity: CTE,
        generation: int,
        limitations: tuple[str, ...],
    ) -> ListPublicationIdentitySummaryDTO | None:
        """Возвращает общие счётчики и полноту последнего чтения, не меняя observed."""
        if policy is None:
            return None
        counts = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count()
                    .filter(identity.c.identity_state == "missing")
                    .label("missing"),
                    func.count()
                    .filter(identity.c.identity_state == "duplicate")
                    .label("duplicate"),
                    func.count()
                    .filter(identity.c.identity_state == "valid")
                    .label("valid"),
                    func.count(func.distinct(identity.c.identity_key))
                    .filter(identity.c.identity_state == "duplicate")
                    .label("duplicate_groups"),
                ).select_from(identity)
            )
        ).one()
        run = (
            await self.session.execute(
                select(
                    SyncRunModel.status,
                    SyncRunModel.read_complete,
                    SyncRunModel.updated_at,
                    SyncRunModel.generation,
                    SyncRunModel.invalid,
                    SyncRunModel.limitations,
                )
                .where(SyncRunModel.connection_id == connection_id)
                .order_by(SyncRunModel.created_at.desc(), SyncRunModel.id.desc())
                .limit(1)
            )
        ).one_or_none()
        assessment = "not_started"
        checked_at = None
        if run is not None:
            checked_at = run.updated_at
            limitations = tuple(dict.fromkeys((*limitations, *run.limitations)))
            if run.generation != generation:
                assessment = "stale"
            elif run.status in ("queued", "running"):
                assessment = "in_progress"
            elif run.read_complete and run.invalid == 0:
                assessment = "current"
            else:
                assessment = "incomplete"
        return ListPublicationIdentitySummaryDTO(
            policy.label,
            counts.total,
            counts.missing,
            counts.duplicate,
            counts.valid,
            counts.duplicate_groups,
            assessment,
            checked_at,
            limitations,
            policy.help_title,
            policy.help_steps,
            policy.help_url,
            policy.recovery_verified,
        )
