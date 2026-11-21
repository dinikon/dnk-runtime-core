from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeCodeAlreadyExistsError,
    PackagingTypeNotFoundError,
    PackagingTypeInUseError,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.mapper import (
    PackagingTypeMapper,
)
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)


class SqlAlchemyPackagingTypeRepository:
    """Записывает тип тары на сессии общего внешнего tenant-UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию без владения транзакцией и выбора схемы."""
        self._session = session

    async def get_for_update(
        self, identifier: PackagingTypeIdVO
    ) -> PackagingType | None:
        """Блокирует корень и перечитывает модель поверх identity map после ожидания."""
        statement = (
            select(PackagingTypeModel)
            .where(PackagingTypeModel.id == identifier.uuid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return PackagingTypeMapper.to_domain(model) if model is not None else None

    async def add(self, packaging_type: PackagingType) -> None:
        """Вставляет агрегат и переводит только известный конфликт точного кода."""
        try:
            await self._session.execute(
                insert(PackagingTypeModel).values(
                    PackagingTypeMapper.to_insert_values(packaging_type)
                )
            )
        except IntegrityError as exc:
            self._raise_code_conflict(exc)
            raise

    async def save(self, packaging_type: PackagingType) -> None:
        """Сохраняет существующий корень и различает отсутствие записи через RETURNING."""
        statement = (
            update(PackagingTypeModel)
            .where(PackagingTypeModel.id == packaging_type.id.uuid)
            .values(PackagingTypeMapper.to_update_values(packaging_type))
            .returning(PackagingTypeModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
        except IntegrityError as exc:
            self._raise_code_conflict(exc)
            raise
        if identifier is None:
            raise PackagingTypeNotFoundError("Тип тары не найден.")

    async def delete(self, packaging_type: PackagingType) -> None:
        """Удаляет корень с RETURNING; защитный FK дополняет доменную проверку использования."""
        statement = (
            delete(PackagingTypeModel)
            .where(PackagingTypeModel.id == packaging_type.id.uuid)
            .returning(PackagingTypeModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
        except IntegrityError as exc:
            cause = getattr(exc.orig, "__cause__", None)
            sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(
                cause, "sqlstate", None
            )
            constraint = getattr(exc.orig, "constraint_name", None) or getattr(
                cause, "constraint_name", None
            )
            # RESTRICT может сообщаться отдельным SQLSTATE 23001.
            if (
                sqlstate in {"23503", "23001"}
                and constraint == "fk_item_packagings_type"
            ):
                raise PackagingTypeInUseError(
                    "Нельзя удалить тип тары: он используется в упаковках товаров. "
                    "Используемый тип можно деактивировать."
                ) from exc
            raise
        if identifier is None:
            raise PackagingTypeNotFoundError("Тип тары не найден.")

    @staticmethod
    def _raise_code_conflict(error: IntegrityError) -> None:
        """Распознаёт именованный UNIQUE, сохраняя причину и неизвестные ошибки БД."""
        cause = getattr(error.orig, "__cause__", None)
        sqlstate = getattr(error.orig, "sqlstate", None) or getattr(
            cause, "sqlstate", None
        )
        constraint = getattr(error.orig, "constraint_name", None) or getattr(
            cause, "constraint_name", None
        )
        if sqlstate == "23505" and constraint == "uq_packaging_types_code":
            raise PackagingTypeCodeAlreadyExistsError(
                "Код типа тары уже занят в текущем tenant."
            ) from error
