from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    AttributeDetailsDTO,
    AttributeOptionDTO,
)
from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.catalog.infrastructure.persistence.models.attribute import (
    AttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_content import (
    AttributeContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option import (
    AttributeOptionModel,
)
from src.modules.catalog.infrastructure.persistence.models.option_content import (
    OptionContentModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyAttributeQueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def option_ids(
        self, attribute_ids: frozenset[UUID]
    ) -> dict[UUID, frozenset[UUID]]:
        if not attribute_ids:
            return {}
        rows = (
            await self._session.execute(
                select(
                    AttributeOptionModel.attribute_id, AttributeOptionModel.id
                ).where(AttributeOptionModel.attribute_id.in_(attribute_ids))
            )
        ).all()
        result: dict[UUID, set[UUID]] = {}
        for attribute_id, option_id in rows:
            result.setdefault(attribute_id, set()).add(option_id)
        return {key: frozenset(value) for key, value in result.items()}

    async def list_details(
        self, locale: AttributeLocaleVO
    ) -> tuple[AttributeDetailsDTO, ...]:
        attributes = (
            await self._session.execute(
                select(
                    AttributeModel.id,
                    AttributeModel.code,
                    AttributeModel.type,
                    AttributeContentModel.name,
                )
                .outerjoin(
                    AttributeContentModel,
                    (AttributeContentModel.attribute_id == AttributeModel.id)
                    & (AttributeContentModel.locale_code == locale.value),
                )
                .order_by(AttributeModel.code)
            )
        ).all()
        if not attributes:
            return ()
        options = (
            await self._session.execute(
                select(
                    AttributeOptionModel.attribute_id,
                    AttributeOptionModel.id,
                    AttributeOptionModel.code,
                    OptionContentModel.name,
                )
                .outerjoin(
                    OptionContentModel,
                    (OptionContentModel.option_id == AttributeOptionModel.id)
                    & (OptionContentModel.locale_code == locale.value),
                )
                .order_by(AttributeOptionModel.code)
            )
        ).all()
        by_attribute: dict[UUID, list[AttributeOptionDTO]] = {}
        for attribute_id, option_id, code, name in options:
            by_attribute.setdefault(attribute_id, []).append(
                AttributeOptionDTO(id=option_id, code=code, name=name)
            )
        return tuple(
            AttributeDetailsDTO(
                id=identifier,
                code=code,
                type=type_,
                name=name,
                options=tuple(by_attribute.get(identifier, ())),
            )
            for identifier, code, type_, name in attributes
        )

    async def get_details(
        self, attribute_id: EntityIdVO, locale: AttributeLocaleVO
    ) -> AttributeDetailsDTO | None:
        row = await self._session.get(AttributeModel, attribute_id.uuid)
        if row is None:
            return None
        attribute_name = await self._session.scalar(
            select(AttributeContentModel.name).where(
                AttributeContentModel.attribute_id == attribute_id.uuid,
                AttributeContentModel.locale_code == locale.value,
            )
        )
        options = (
            await self._session.execute(
                select(
                    AttributeOptionModel.id,
                    AttributeOptionModel.code,
                    OptionContentModel.name,
                )
                .outerjoin(
                    OptionContentModel,
                    (OptionContentModel.option_id == AttributeOptionModel.id)
                    & (OptionContentModel.locale_code == locale.value),
                )
                .where(AttributeOptionModel.attribute_id == attribute_id.uuid)
                .order_by(AttributeOptionModel.code)
            )
        ).all()
        return AttributeDetailsDTO(
            id=row.id,
            code=row.code,
            type=row.type,
            name=attribute_name,
            options=tuple(
                AttributeOptionDTO(id=option_id, code=code, name=name)
                for option_id, code, name in options
            ),
        )
