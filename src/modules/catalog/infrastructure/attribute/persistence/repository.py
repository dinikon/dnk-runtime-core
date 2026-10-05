from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.attribute.aggregate import Attribute
from src.modules.catalog.domain.attribute.error import AttributeAlreadyExistsError
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


class SqlAlchemyAttributeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, attribute: Attribute) -> None:
        try:
            await self._session.execute(
                insert(AttributeModel).values(
                    id=attribute.id.uuid,
                    code=attribute.code,
                    type=attribute.type,
                    created_at=attribute.created_at,
                    updated_at=attribute.updated_at,
                    created_by=attribute.created_by.uuid,
                    updated_by=attribute.updated_by.uuid,
                )
            )
            await self._session.execute(
                insert(AttributeOptionModel),
                [
                    dict(
                        id=item.id.uuid, attribute_id=attribute.id.uuid, code=item.code
                    )
                    for item in attribute.options
                ],
            )
            if attribute.contents:
                await self._session.execute(
                    insert(AttributeContentModel),
                    [
                        dict(
                            attribute_id=attribute.id.uuid,
                            locale_code=item.locale.value,
                            name=item.name,
                        )
                        for item in attribute.contents
                    ],
                )
            option_contents = [
                dict(
                    option_id=option.id.uuid,
                    locale_code=item.locale.value,
                    name=item.name,
                )
                for option in attribute.options
                for item in option.contents
            ]
            if option_contents:
                await self._session.execute(insert(OptionContentModel), option_contents)
        except IntegrityError as exc:
            original = exc.orig
            constraint = getattr(original, "constraint_name", None) or getattr(
                original.__cause__, "constraint_name", None
            )
            if getattr(original, "sqlstate", None) == "23505" and constraint == (
                "uq_catalog_attributes_code"
            ):
                raise AttributeAlreadyExistsError(
                    "Attribute code already exists."
                ) from exc
            raise
