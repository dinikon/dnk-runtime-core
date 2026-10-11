from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.infrastructure.persistence.models.attribute import (
    AttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option import (
    AttributeOptionModel,
)


class SqlAlchemyAttributeDefinitions:
    """Читает минимальные определения enum одним batch."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую tenant-сессию."""
        self._session = session

    async def get_definitions(
        self, identifiers: tuple[AttributeIdVO, ...]
    ) -> tuple[EnumAttributeSnapshot, ...]:
        """Возвращает только существующие определения и принадлежащие им options."""
        rows = (
            await self._session.execute(
                select(AttributeModel.id, AttributeOptionModel.id.label("option_id"))
                .outerjoin(
                    AttributeOptionModel,
                    AttributeOptionModel.attribute_id == AttributeModel.id,
                )
                .where(AttributeModel.id.in_(tuple(i.uuid for i in identifiers)))
            )
        ).all()
        grouped = {}
        for row in rows:
            grouped.setdefault(row.id, set())
            if row.option_id is not None:
                grouped[row.id].add(AttributeOptionIdVO(row.option_id))
        return tuple(
            EnumAttributeSnapshot(AttributeIdVO(i), frozenset(options))
            for i, options in grouped.items()
        )
