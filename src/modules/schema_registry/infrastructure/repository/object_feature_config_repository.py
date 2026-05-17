from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
from src.modules.schema_registry.domain.object_feature.repository import (
    ObjectFeatureConfigRepositoryProtocol,
)
from src.modules.schema_registry.domain.object_feature.value_object import (
    FeatureCodeVO,
    ObjectFeatureConfigIdVO,
    ObjectFeatureKind,
    ObjectFeatureStatus,
)
from src.modules.schema_registry.infrastructure.persistence.object_feature_config import (
    ObjectFeatureConfigORM,
)
from src.modules.shared import EntityIdVO


class SqlAlchemyObjectFeatureConfigRepository(
    ObjectFeatureConfigRepositoryProtocol,
):
    """SQLAlchemy-репозиторий feature config runtime-объектов."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий текущей async-сессией."""
        self._session = session

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
        feature_code: FeatureCodeVO,
    ) -> ObjectFeatureConfigEntity | None:
        """Ищет feature config по tenant/object/feature."""
        model = await self._session.scalar(
            select(ObjectFeatureConfigORM)
            .where(ObjectFeatureConfigORM.tenant_id == tenant_id.uuid)
            .where(ObjectFeatureConfigORM.object_id == object_id.uuid)
            .where(ObjectFeatureConfigORM.feature_code == feature_code.value)
            .limit(1)
        )
        if model is None:
            return None
        return self._map_model(model)

    async def save(self, config: ObjectFeatureConfigEntity) -> None:
        """Сохраняет feature config без управления transaction lifecycle."""
        model = await self._session.get(
            ObjectFeatureConfigORM,
            config.id.uuid,
        )
        if model is None:
            self._session.add(self._to_model(config))
        else:
            self._update_model(model, config)
        await self._session.flush()

    async def list_by_object(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> list[ObjectFeatureConfigEntity]:
        """Возвращает feature configs объекта tenant в стабильном порядке."""
        models = (
            await self._session.scalars(
                select(ObjectFeatureConfigORM)
                .where(ObjectFeatureConfigORM.tenant_id == tenant_id.uuid)
                .where(ObjectFeatureConfigORM.object_id == object_id.uuid)
                .order_by(
                    ObjectFeatureConfigORM.created_at,
                    ObjectFeatureConfigORM.object_feature_config_id,
                )
            )
        ).all()
        return [self._map_model(model) for model in models]

    @staticmethod
    def _to_model(config: ObjectFeatureConfigEntity) -> ObjectFeatureConfigORM:
        """Мапит доменную ObjectFeatureConfigEntity в SQLAlchemy-модель."""
        return ObjectFeatureConfigORM(
            object_feature_config_id=config.id.uuid,
            created_at=config.created_at,
            updated_at=config.updated_at,
            tenant_id=config.tenant_id.uuid,
            object_id=config.object_id.uuid,
            feature_code=config.feature_code.value,
            kind=config.kind.value,
            status=config.status.value,
            config=dict(config.config),
            is_locked=config.is_locked,
            locked_reason=config.locked_reason,
        )

    @staticmethod
    def _update_model(
        model: ObjectFeatureConfigORM,
        config: ObjectFeatureConfigEntity,
    ) -> None:
        """Копирует изменяемые поля entity в существующую ORM-модель."""
        model.tenant_id = config.tenant_id.uuid
        model.object_id = config.object_id.uuid
        model.feature_code = config.feature_code.value
        model.kind = config.kind.value
        model.status = config.status.value
        model.config = dict(config.config)
        model.is_locked = config.is_locked
        model.locked_reason = config.locked_reason
        model.updated_at = config.updated_at

    @staticmethod
    def _map_model(model: ObjectFeatureConfigORM) -> ObjectFeatureConfigEntity:
        """Мапит SQLAlchemy-модель feature config в доменную entity."""
        return ObjectFeatureConfigEntity(
            id=ObjectFeatureConfigIdVO.from_value(model.object_feature_config_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            object_id=RuntimeObjectIdVO.from_value(model.object_id),
            feature_code=FeatureCodeVO(model.feature_code),
            kind=ObjectFeatureKind(model.kind),
            status=ObjectFeatureStatus(model.status),
            config=dict(model.config or {}),
            is_locked=model.is_locked,
            locked_reason=model.locked_reason,
        )
