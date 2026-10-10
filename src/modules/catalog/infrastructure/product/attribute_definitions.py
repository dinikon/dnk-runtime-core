from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.attribute.error import AttributeNotFoundError
from src.modules.catalog.domain.product.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.infrastructure.persistence.models.attribute import (
    AttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option import (
    AttributeOptionModel,
)


class SqlAlchemyAttributeDefinitions:
    """Читает минимальные immutable снимки определений для Product."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant-сессию процесса."""
        self._session = session

    async def get_definitions(
        self, identifiers: tuple[AttributeIdVO, ...]
    ) -> tuple[EnumAttributeSnapshot, ...]:
        """Проверяет наличие определений и собирает допустимые значения enum."""
        if not identifiers:
            return ()
        ids = tuple(i.uuid for i in identifiers)
        existing = set(
            (
                await self._session.scalars(
                    select(AttributeModel.id).where(AttributeModel.id.in_(ids))
                )
            ).all()
        )
        if set(ids) - existing:
            raise AttributeNotFoundError(
                "Товар ссылается на отсутствующую характеристику."
            )
        rows = (
            await self._session.execute(
                select(
                    AttributeOptionModel.attribute_id, AttributeOptionModel.id
                ).where(AttributeOptionModel.attribute_id.in_(ids))
            )
        ).all()
        return tuple(
            EnumAttributeSnapshot(
                identifier,
                frozenset(
                    AttributeOptionIdVO(o) for a, o in rows if a == identifier.uuid
                ),
            )
            for identifier in identifiers
        )
