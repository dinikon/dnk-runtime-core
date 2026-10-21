from uuid import UUID
from sqlalchemy import (
    select,
    insert,
    update,
    literal,
    cast,
    String,
    Integer,
    Boolean,
    or_,
    exists,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.batch_export.aggregate import BatchExportRun, ACTIVE
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.channels.infrastructure.persistence.models.batch_export import (
    BatchExportRunModel as R,
    BatchExportItemModel as I,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as P,
)
from src.modules.channels.infrastructure.persistence.models.external_binding import (
    ExternalBindingModel as B,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as E,
)
from src.modules.channels.infrastructure.batch_export.persistence.mapper import (
    BatchExportMapper as Mapper,
)


class SqlAlchemyBatchExportRepository:
    """Пишет только собственные таблицы и фиксирует состав пакета одним INSERT SELECT."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего tenant UoW."""
        self.session = session

    async def find(self, identifier: UUID) -> BatchExportRun | None:
        """Читает и блокирует корень после блокировки Channel."""
        row = (
            (
                await self.session.execute(
                    select(R.__table__).where(R.id == identifier).with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return Mapper.run(row) if row else None

    async def get(self, identifier: UUID) -> BatchExportRun:
        """Возвращает предметный not found для отсутствующей операции."""
        run = await self.find(identifier)
        if run is None:
            raise ChannelsNotFoundError("batch_export_not_found")
        return run

    async def active(self, connection_id: UUID) -> BatchExportRun | None:
        """Читает единственный слот, включая неопределённую отправку."""
        identifier = await self.session.scalar(
            select(R.id).where(R.connection_id == connection_id, R.status.in_(ACTIVE))
        )
        return await self.get(identifier) if identifier else None

    async def add(self, run: BatchExportRun) -> None:
        """Фиксирует все разрешённые активные связи без лимита размера пакета."""
        await self.session.execute(insert(R).values(**Mapper.values(run)))
        columns = [
            "run_id",
            "publication_id",
            "catalog_item_id",
            "binding_id",
            "representation_id",
            "binding_revision",
            "external_id",
            "provider_context",
            "desired",
            "baseline",
            "status",
            "issues",
            "identity_key",
            "identity_count",
            "identity_native_ok",
        ]
        snapshot = (
            select(
                literal(run.id),
                E.id,
                P.catalog_item_id,
                B.id,
                P.id,
                P.revision,
                E.external_id,
                E.meta["provider"],
                cast(literal(None), JSONB()),
                cast(literal(None), JSONB()),
                literal("pending"),
                cast(literal("[]"), JSONB()),
                cast(literal(None), String(512)),
                literal(0),
                literal(True),
            )
            .select_from(P)
            .join(B, B.representation_id == P.id)
            .join(E, E.id == B.publication_id)
            .where(
                P.connection_id == run.connection_id,
                P.export_enabled.is_(True),
                B.released_at.is_(None),
                E.connection_id == run.connection_id,
            )
        )
        await self.session.execute(insert(I).from_select(columns, snapshot))

    async def save(
        self, run: BatchExportRun, items: tuple[ExportItemVO, ...] = ()
    ) -> None:
        """Сохраняет результаты ограниченной части и переход корня атомарно."""
        await self.session.execute(
            update(R).where(R.id == run.id).values(**Mapper.values(run))
        )
        for item in items:
            await self.session.execute(
                update(I)
                .where(I.run_id == run.id, I.publication_id == item.publication_id)
                .values(**Mapper.item_values(item))
            )

    async def page(
        self, run_id: UUID, status: str, after: UUID | None = None, limit: int = 100
    ) -> tuple[ExportItemVO, ...]:
        """Использует keyset и составной индекс без OFFSET на больших пакетах."""
        conditions = [I.run_id == run_id, I.status == status]
        if after is not None:
            conditions.append(I.publication_id > after)
        rows = (
            await self.session.execute(
                select(I.__table__)
                .where(*conditions)
                .order_by(I.publication_id)
                .limit(min(limit, 100))
            )
        ).mappings()
        return tuple(Mapper.item(row) for row in rows)

    async def matching(
        self, run_id: UUID, keys: tuple[str, ...], native_ids: tuple[str, ...]
    ) -> tuple[ExportItemVO, ...]:
        """Сопоставляет ограниченную страницу с целями снимка через индексы."""
        rows = (
            await self.session.execute(
                select(I.__table__).where(
                    I.run_id == run_id,
                    I.status == "ready",
                    or_(I.identity_key.in_(keys), I.external_id.in_(native_ids)),
                )
            )
        ).mappings()
        return tuple(Mapper.item(row) for row in rows)

    async def counts(self, run_id: UUID) -> dict[str, int]:
        """Считает результат пакета без загрузки его позиций."""
        return dict(
            (
                await self.session.execute(
                    select(I.status, func.count())
                    .where(I.run_id == run_id)
                    .group_by(I.status)
                )
            ).all()
        )

    async def current(self, run_id: UUID) -> bool:
        """Сравнивает всю зафиксированную связь и разрешение перед отправкой."""
        invalid = (
            select(I.publication_id)
            .select_from(I)
            .outerjoin(B, B.id == I.binding_id)
            .outerjoin(P, P.id == I.representation_id)
            .outerjoin(E, E.id == I.publication_id)
            .where(
                I.run_id == run_id,
                I.status == "ready",
                or_(
                    B.id.is_(None),
                    B.released_at.is_not(None),
                    P.id.is_(None),
                    P.revision != I.binding_revision,
                    P.export_enabled.is_(False),
                    P.catalog_item_id != I.catalog_item_id,
                    B.publication_id != I.publication_id,
                    E.external_id != I.external_id,
                ),
            )
        )
        return not bool(await self.session.scalar(select(exists(invalid))))

    async def identities_valid(self, run_id: UUID) -> bool:
        """Запрещает отправку ключей, отсутствующих или дублирующихся во внешнем источнике."""
        return not bool(
            await self.session.scalar(
                select(
                    exists(
                        select(I.publication_id).where(
                            I.run_id == run_id,
                            I.status == "ready",
                            or_(I.identity_count != 1, I.identity_native_ok.is_(False)),
                        )
                    )
                )
            )
        )

    async def invalid_identities(self, run_id: UUID) -> tuple[ExportItemVO, ...]:
        """Выбирает ограниченную часть конфликтов до сборки файла."""
        rows = (
            await self.session.execute(
                select(I.__table__)
                .where(
                    I.run_id == run_id,
                    I.status == "ready",
                    or_(I.identity_count != 1, I.identity_native_ok.is_(False)),
                )
                .order_by(I.publication_id)
                .limit(100)
            )
        ).mappings()
        return tuple(Mapper.item(row) for row in rows)

    async def reopen_verification(self, run_id: UUID) -> None:
        """Возвращает неопределённые позиции только в очередь чтения."""
        await self.session.execute(
            update(I)
            .where(I.run_id == run_id, I.status == "unknown")
            .values(status="ready")
        )
