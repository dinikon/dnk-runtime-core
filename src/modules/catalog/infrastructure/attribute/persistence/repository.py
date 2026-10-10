from src.modules.catalog.infrastructure.persistence.models.product_attribute_value import (
    ProductAttributeValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute import (
    AttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_translation import (
    AttributeTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option import (
    AttributeOptionModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option_translation import (
    AttributeOptionTranslationModel,
)

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.attribute.aggregate import AttributeDefinition
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.attribute.error import AttributeNotFoundError
from src.modules.catalog.infrastructure.persistence.models.product_axis import (
    ProductAxisModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_axis_option import (
    ProductAxisOptionModel,
)
from src.modules.catalog.infrastructure.attribute.persistence.mapper import (
    AttributeMapper,
)
from src.modules.catalog.infrastructure.attribute.persistence.rows import (
    read_attribute_parts,
)


class SqlAlchemyAttributeRepository:
    """Хранит полный агрегат определения на общей tenant-сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего UoW без выбора tenant и commit."""
        self._session = session

    async def get(self, identifier: AttributeIdVO) -> AttributeDefinition:
        """Восстанавливает агрегат после чтения его собственных частей."""
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
            raise AttributeNotFoundError("Характеристика отсутствует.")
        translations, options = await read_attribute_parts(
            self._session, identifier.uuid
        )
        return AttributeMapper.to_domain(row, translations, options)

    async def add(self, entity: AttributeDefinition) -> None:
        """Добавляет определение и его сущности без commit."""
        await self._session.execute(
            insert(AttributeModel).values(AttributeMapper.to_insert_values(entity))
        )
        await self._save_parts(entity)

    async def save(self, entity: AttributeDefinition) -> None:
        """Сохраняет проверенные изменения, не удаляя используемые options."""
        await self._session.execute(
            update(AttributeModel)
            .where(AttributeModel.id == entity.id.uuid)
            .values(AttributeMapper.to_update_values(entity))
        )
        await self._save_parts(entity)

    async def _save_parts(self, entity: AttributeDefinition) -> None:
        """Синхронизирует собственные строки в порядке внешних ключей."""
        await self._session.execute(
            delete(AttributeTranslationModel).where(
                AttributeTranslationModel.attribute_id == entity.id.uuid
            )
        )
        if entity.translations:
            await self._session.execute(
                insert(AttributeTranslationModel),
                [
                    {"attribute_id": entity.id.uuid, "locale": k, "label": v}
                    for k, v in entity.translations.items()
                ],
            )
        existing = set(
            (
                await self._session.scalars(
                    select(AttributeOptionModel.id).where(
                        AttributeOptionModel.attribute_id == entity.id.uuid
                    )
                )
            ).all()
        )
        incoming = {o.id.uuid for o in entity.options}
        removed = existing - incoming
        if removed:
            await self._session.execute(
                delete(AttributeOptionModel).where(AttributeOptionModel.id.in_(removed))
            )
        for position, option in enumerate(entity.options):
            values = {
                "attribute_id": entity.id.uuid,
                "code": option.code.value,
                "position": position,
            }
            if option.id.uuid in existing:
                await self._session.execute(
                    update(AttributeOptionModel)
                    .where(AttributeOptionModel.id == option.id.uuid)
                    .values(**values)
                )
            else:
                await self._session.execute(
                    insert(AttributeOptionModel).values(id=option.id.uuid, **values)
                )
            await self._session.execute(
                delete(AttributeOptionTranslationModel).where(
                    AttributeOptionTranslationModel.option_id == option.id.uuid
                )
            )
            if option.translations:
                await self._session.execute(
                    insert(AttributeOptionTranslationModel),
                    [
                        {"option_id": option.id.uuid, "locale": k, "label": v}
                        for k, v in option.translations.items()
                    ],
                )

    async def delete(self, entity: AttributeDefinition) -> None:
        """Удаляет агрегат после доменной проверки использования."""
        await self._session.execute(
            delete(AttributeModel).where(AttributeModel.id == entity.id.uuid)
        )

    async def is_used(self, identifier: AttributeIdVO) -> bool:
        """Проверяет наличие осей, ссылающихся на определение."""
        return bool(
            await self._session.scalar(
                select(ProductAttributeValueModel.product_id)
                .where(ProductAttributeValueModel.attribute_id == identifier.uuid)
                .limit(1)
            )
        ) or bool(
            await self._session.scalar(
                select(ProductAxisModel.attribute_id)
                .where(ProductAxisModel.attribute_id == identifier.uuid)
                .limit(1)
            )
        )

    async def used_options(
        self, identifier: AttributeIdVO
    ) -> frozenset[AttributeOptionIdVO]:
        """Читает разрешённые options всех осей, а не только выбранных позиций."""
        ids = (
            await self._session.scalars(
                select(ProductAxisOptionModel.option_id).where(
                    ProductAxisOptionModel.attribute_id == identifier.uuid
                )
            )
        ).all()
        general = (
            await self._session.scalars(
                select(ProductAttributeValueModel.option_id).where(
                    ProductAttributeValueModel.attribute_id == identifier.uuid
                )
            )
        ).all()
        return frozenset(
            AttributeOptionIdVO(identifier) for identifier in (*ids, *general)
        )
