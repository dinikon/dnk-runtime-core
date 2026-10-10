from src.modules.catalog.infrastructure.persistence.models.attribute import (
    AttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_translation import (
    AttributeTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option import (
    AttributeOptionModel,
)

from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.application.attribute.query.get_attribute.dto import (
    GetAttributeDetailsDTO,
)
from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    ListAttributesPageDTO,
)
from src.modules.catalog.infrastructure.attribute.persistence.query_mapper import (
    AttributeQueryMapper,
)
from src.modules.catalog.infrastructure.attribute.persistence.rows import (
    read_attribute_parts,
)


class SqlAlchemyAttributeQueryRepository:
    """Читает enum-проекции, не восстанавливая Domain-агрегат."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant-сессию внешнего UoW."""
        self._session = session

    async def get_details(
        self, identifier: AttributeIdVO, locale: str
    ) -> GetAttributeDetailsDTO | None:
        """Читает определение с options без подмены отсутствующих переводов."""
        row = (
            (
                await self._session.execute(
                    select(AttributeModel.__table__).where(
                        AttributeModel.id == identifier.uuid
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        translations, options = await read_attribute_parts(
            self._session, identifier.uuid
        )
        return AttributeQueryMapper.to_details(row, translations, options, locale)

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListAttributesPageDTO:
        """Считает определения до пагинации, не размножая строки options."""
        statement = select(
            AttributeModel.__table__,
            AttributeTranslationModel.label,
            select(func.count())
            .select_from(AttributeOptionModel)
            .where(AttributeOptionModel.attribute_id == AttributeModel.id)
            .correlate(AttributeModel)
            .scalar_subquery()
            .label("option_count"),
        ).outerjoin(
            AttributeTranslationModel,
            (AttributeTranslationModel.attribute_id == AttributeModel.id)
            & (AttributeTranslationModel.locale == locale),
        )
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            statement = statement.where(
                or_(
                    AttributeModel.code.ilike("%" + escaped + "%", escape="\\"),
                    AttributeTranslationModel.label.ilike(
                        "%" + escaped + "%", escape="\\"
                    ),
                    cast(AttributeModel.id, String).ilike(
                        "%" + escaped + "%", escape="\\"
                    ),
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(
                        AttributeModel.created_at.desc(), AttributeModel.id
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .mappings()
            .all()
        )
        return ListAttributesPageDTO(
            tuple(AttributeQueryMapper.to_list_item(r) for r in rows),
            total or 0,
            page,
            page_size,
        )
