from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.policy.schema_structure import (
    FeedSchemaStructurePolicy,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.error import (
    InvalidFeedValueError,
    FeedArchivedError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.validation import require_datetime
from src.modules.feed_builder.domain.feed.policy.schema_sources import (
    FeedSchemaSourcePolicy,
)


@dataclass(frozen=True, slots=True)
class Feed:
    """Корневой агрегат пользовательской схемы и настроек выгрузки."""

    id: FeedIdVO
    created_at: datetime
    updated_at: datetime
    name: FeedNameVO
    code: FeedCodeVO
    status: FeedStatus
    schema: FeedSchemaVO
    export_settings: FeedExportSettingsVO
    version: FeedVersionVO = FeedVersionVO(1)

    @classmethod
    def create(
        cls,
        *,
        identifier: FeedIdVO,
        name: FeedNameVO,
        code: FeedCodeVO,
        now: datetime,
        export_settings: FeedExportSettingsVO,
        schema: FeedSchemaVO | None = None,
    ) -> Self:
        """Создаёт DRAFT с явными настройками экспорта и пустой либо переданной схемой."""
        return cls.restore(
            identifier=identifier,
            name=name,
            code=code,
            status=FeedStatus.DRAFT,
            schema=FeedSchemaVO() if schema is None else schema,
            export_settings=export_settings,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FeedIdVO,
        name: FeedNameVO,
        code: FeedCodeVO,
        status: FeedStatus,
        schema: FeedSchemaVO,
        export_settings: FeedExportSettingsVO,
        created_at: datetime,
        updated_at: datetime,
        version: FeedVersionVO = FeedVersionVO(1),
    ) -> Self:
        """Восстанавливает состав и проверяет собственные инварианты без I/O."""
        if (
            not isinstance(identifier, FeedIdVO)
            or not isinstance(name, FeedNameVO)
            or not isinstance(code, FeedCodeVO)
            or not isinstance(status, FeedStatus)
            or not isinstance(schema, FeedSchemaVO)
            or not isinstance(export_settings, FeedExportSettingsVO)
            or not isinstance(version, FeedVersionVO)
        ):
            raise InvalidFeedValueError("Нужны типизированные свойства Feed.")
        for value in (created_at, updated_at):
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise InvalidFeedValueError("Даты Feed должны иметь timezone.")
        if updated_at < created_at:
            raise InvalidFeedValueError(
                "Изменение Feed не может предшествовать созданию."
            )
        schema = FeedSchemaStructurePolicy.validate(schema)
        return cls(
            id=identifier,
            name=name,
            code=code,
            status=status,
            schema=schema,
            export_settings=export_settings,
            created_at=created_at,
            updated_at=updated_at,
            version=version,
        )

    def change_settings(
        self,
        *,
        name: FeedNameVO,
        code: FeedCodeVO,
        export_settings: FeedExportSettingsVO,
        now: datetime,
    ) -> Self:
        """Атомарно возвращает новое состояние настроек, сохраняя схему и идентичность."""
        require_datetime(now, error=InvalidFeedValueError)
        if now < self.updated_at:
            raise InvalidFeedValueError("Время изменения не может двигаться назад.")
        if self.status is FeedStatus.ARCHIVED:
            raise FeedArchivedError("Архивный Feed нельзя редактировать.")
        if (
            not isinstance(name, FeedNameVO)
            or not isinstance(code, FeedCodeVO)
            or not isinstance(export_settings, FeedExportSettingsVO)
        ):
            raise InvalidFeedValueError("Нужны типизированные настройки Feed.")
        if (name, code, export_settings) == (
            self.name,
            self.code,
            self.export_settings,
        ):
            return self
        return self.restore(
            identifier=self.id,
            name=name,
            code=code,
            status=self.status,
            schema=self.schema,
            export_settings=export_settings,
            created_at=self.created_at,
            updated_at=now,
            version=FeedVersionVO(self.version.value + 1),
        )

    def change_schema(self, *, schema: FeedSchemaVO, now: datetime) -> Self:
        """Атомарно заменяет рабочее определение через корень без публикации или ревизий."""
        require_datetime(now, error=InvalidFeedValueError)
        if now < self.updated_at:
            raise InvalidFeedValueError("Время изменения не может двигаться назад.")
        if self.status is FeedStatus.ARCHIVED:
            raise FeedArchivedError("Архивный Feed нельзя редактировать.")
        checked = FeedSchemaStructurePolicy.validate(schema)
        FeedSchemaSourcePolicy.ensure_valid(checked)
        if checked == self.schema:
            return self
        return self.restore(
            identifier=self.id,
            name=self.name,
            code=self.code,
            status=self.status,
            schema=checked,
            export_settings=self.export_settings,
            created_at=self.created_at,
            updated_at=now,
            version=FeedVersionVO(self.version.value + 1),
        )

    def archive(self, *, now: datetime) -> Self:
        """Возвращает архивное состояние с новой версией либо исходный архивный объект."""
        require_datetime(now, error=InvalidFeedValueError)
        if now < self.updated_at:
            raise InvalidFeedValueError("Время архивации не может двигаться назад.")
        if self.status is FeedStatus.ARCHIVED:
            return self
        return self.restore(
            identifier=self.id,
            name=self.name,
            code=self.code,
            status=FeedStatus.ARCHIVED,
            schema=self.schema,
            export_settings=self.export_settings,
            created_at=self.created_at,
            updated_at=now,
            version=FeedVersionVO(self.version.value + 1),
        )
