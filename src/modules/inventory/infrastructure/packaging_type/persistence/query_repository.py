from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.packaging_type.query.get_packaging_type.query import (
    GetPackagingTypeQuery,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.dto import (
    GetPackagingTypeResultDTO,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.query import (
    ListPackagingTypesQuery,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.dto import (
    ListPackagingTypesResultDTO,
)
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.query_mapper import (
    PackagingTypeQueryMapper,
)


class SqlAlchemyPackagingTypeQueryRepository:
    """Читает проекции типов тары текущего tenant без восстановления агрегатов."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию общего внешнего UoW с выбранной tenant-схемой."""
        self._session = session

    async def get_details(
        self, query: GetPackagingTypeQuery
    ) -> GetPackagingTypeResultDTO | None:
        """Читает актуальную карточку одним типизированным SELECT."""
        statement = (
            select(PackagingTypeModel)
            .where(PackagingTypeModel.id == query.packaging_type_id.uuid)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return PackagingTypeQueryMapper.to_details(model) if model is not None else None

    async def list(self, query: ListPackagingTypesQuery) -> ListPackagingTypesResultDTO:
        """Применяет одинаковые фильтры к total и странице со стабильным порядком."""
        filters: tuple[ColumnElement[bool], ...] = ()
        if query.search is not None:
            filters += (
                or_(
                    PackagingTypeModel.code.collate("default").icontains(
                        query.search, autoescape=True
                    ),
                    PackagingTypeModel.name.icontains(query.search, autoescape=True),
                ),
            )
        if query.is_active is not None:
            filters += (PackagingTypeModel.is_active.is_(query.is_active),)
        total = await self._session.execute(
            select(func.count()).select_from(PackagingTypeModel).where(*filters)
        )
        statement = (
            select(PackagingTypeModel)
            .where(*filters)
            .order_by(PackagingTypeModel.code, PackagingTypeModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        models = (await self._session.scalars(statement)).all()
        return ListPackagingTypesResultDTO(
            items=tuple(
                PackagingTypeQueryMapper.to_list_item(model) for model in models
            ),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
