"""Сохраняемый снимок одной реальной публикации внешнего источника."""

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
import json

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationKind,
)


@dataclass(slots=True)
class ExternalPublication:
    """Сохраняет идентичность независимо от запусков и защищает свой снимок."""

    id: EntityIdVO
    connection_id: EntityIdVO
    resource_type: str
    external_id: str
    kind: PublicationKind
    parent_id: EntityIdVO | None
    revision: int
    _raw_data: JsonObject
    data: PublicationData
    platform_schema: str
    _platform_data: JsonObject
    first_seen_at: datetime
    last_seen_at: datetime
    last_sync_run_id: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        publication_id: EntityIdVO,
        connection_id: EntityIdVO,
        resource_type: str,
        external_id: str,
        kind: PublicationKind,
        parent_id: EntityIdVO | None,
        raw_data: JsonObject,
        data: PublicationData,
        platform_schema: str,
        platform_data: JsonObject,
        run_id: EntityIdVO,
        now: datetime,
    ) -> "ExternalPublication":
        """Создаёт публикацию, проверяя все собственные инварианты."""
        return cls.restore(
            publication_id=publication_id,
            connection_id=connection_id,
            resource_type=resource_type,
            external_id=external_id,
            kind=kind,
            parent_id=parent_id,
            revision=1,
            raw_data=raw_data,
            data=data,
            platform_schema=platform_schema,
            platform_data=platform_data,
            first_seen_at=now,
            last_seen_at=now,
            run_id=run_id,
        )

    @classmethod
    def restore(
        cls,
        *,
        publication_id: EntityIdVO,
        connection_id: EntityIdVO,
        resource_type: str,
        external_id: str,
        kind: PublicationKind,
        parent_id: EntityIdVO | None,
        revision: int,
        raw_data: JsonObject,
        data: PublicationData,
        platform_schema: str,
        platform_data: JsonObject,
        first_seen_at: datetime,
        last_seen_at: datetime,
        run_id: EntityIdVO,
    ) -> "ExternalPublication":
        """Отклоняет некорректное сохранённое состояние без автоматического ремонта."""
        if (
            not all(
                isinstance(value, EntityIdVO)
                for value in (publication_id, connection_id, run_id)
            )
            or not all(
                isinstance(value, str) and value.strip()
                for value in (resource_type, external_id, platform_schema)
            )
            or not isinstance(kind, PublicationKind)
            or len(resource_type) > 64
            or len(external_id.encode("utf-8")) > 512
            or len(platform_schema) > 100
            or type(revision) is not int
            or revision < 1
            or not isinstance(raw_data, dict)
            or not isinstance(platform_data, dict)
            or not isinstance(data, PublicationData)
            or ((kind is PublicationKind.VARIANT) != (parent_id is not None))
            or (
                parent_id is not None
                and (
                    not isinstance(parent_id, EntityIdVO) or parent_id == publication_id
                )
            )
            or not isinstance(first_seen_at, datetime)
            or not isinstance(last_seen_at, datetime)
            or first_seen_at.tzinfo is None
            or last_seen_at.tzinfo is None
            or last_seen_at < first_seen_at
            or (data.stock_mode == "parent" and kind is not PublicationKind.VARIANT)
            or (data.inherit_title and kind is not PublicationKind.VARIANT)
        ):
            raise InvalidExternalPublicationError("Некорректное состояние публикации.")
        try:
            json.dumps([raw_data, platform_data], allow_nan=False)
        except (TypeError, ValueError):
            raise InvalidExternalPublicationError(
                "Документы публикации должны быть JSON."
            ) from None
        return cls(
            publication_id,
            connection_id,
            resource_type,
            external_id,
            kind,
            parent_id,
            revision,
            deepcopy(raw_data),
            data,
            platform_schema,
            deepcopy(platform_data),
            first_seen_at,
            last_seen_at,
            run_id,
        )

    @property
    def raw_data(self) -> JsonObject:
        """Возвращает независимую копию исходного ответа."""
        return deepcopy(self._raw_data)

    @property
    def platform_data(self) -> JsonObject:
        """Возвращает независимую копию нативных сведений."""
        return deepcopy(self._platform_data)

    def observe(
        self,
        *,
        kind: PublicationKind,
        parent_id: EntityIdVO | None,
        raw_data: JsonObject,
        data: PublicationData,
        platform_schema: str,
        platform_data: JsonObject,
        run_id: EntityIdVO,
        now: datetime,
        source_started_at: datetime | None = None,
        config_revision: int | None = None,
    ) -> None:
        """Атомарно заменяет снимок, сохраняя EntityIdVO и первую дату получения."""
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now < self.last_seen_at
        ):
            raise InvalidExternalPublicationError(
                "Наблюдение старше сохранённого снимка."
            )
        stock_observation = self._platform_data.get("stock_observation")
        if (
            source_started_at is not None
            and isinstance(stock_observation, dict)
            and stock_observation.get("config_revision") == config_revision
        ):
            received_at = datetime.fromisoformat(stock_observation["received_at"])
            if received_at > source_started_at:
                # Полный ответ был запрошен до отдельного получения/отправки остатка.
                data = replace(
                    data,
                    quantity=self.data.quantity,
                    stock_mode=self.data.stock_mode,
                    availability=self.data.availability,
                )
                platform_data = {
                    **platform_data,
                    "stock_observation": stock_observation,
                }
        candidate = self.restore(
            publication_id=self.id,
            connection_id=self.connection_id,
            resource_type=self.resource_type,
            external_id=self.external_id,
            kind=kind,
            parent_id=parent_id,
            revision=self.revision,
            raw_data=raw_data,
            data=data,
            platform_schema=platform_schema,
            platform_data=platform_data,
            first_seen_at=self.first_seen_at,
            last_seen_at=now,
            run_id=run_id,
        )
        changed = (
            self.kind != kind
            or self.parent_id != parent_id
            or self.data != data
            or self._raw_data != candidate._raw_data
            or self.platform_schema != platform_schema
            or self._platform_data != candidate._platform_data
        )
        self.kind, self.parent_id = kind, parent_id
        self._raw_data, self.data = candidate._raw_data, data
        self.platform_schema, self._platform_data = (
            platform_schema,
            candidate._platform_data,
        )
        self.last_seen_at, self.last_sync_run_id = now, run_id
        self.revision += int(changed)

    def observe_stock(
        self,
        *,
        quantity: Decimal | None,
        stock_mode: str,
        availability: str | None,
        native: JsonObject,
        now: datetime,
    ) -> None:
        """Меняет только наблюдение остатка, сохраняя полный исходный снимок контента."""
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or (stock_mode == "parent" and self.parent_id is None)
        ):
            raise InvalidExternalPublicationError("Некорректное наблюдение остатка.")
        candidate = replace(
            self.data,
            quantity=quantity,
            stock_mode=stock_mode,
            availability=availability,
        )
        document = deepcopy(native)
        try:
            json.dumps(document, allow_nan=False)
        except (ValueError, TypeError):
            raise InvalidExternalPublicationError(
                "Наблюдение должно быть JSON."
            ) from None
        self.data = candidate
        self._platform_data = {
            **self._platform_data,
            "stock_observation": {
                **document,
                "version": 1,
                "received_at": now.isoformat(),
            },
        }
        self.revision += 1


class PublicationStructurePolicy:
    """Проверяет согласованный результат изменения нескольких публикаций."""

    def ensure_valid(
        self,
        publications: tuple[ExternalPublication, ...],
        *,
        required_parent_kind: PublicationKind | None = None,
    ) -> None:
        """Запрещает чужого родителя, самоссылку и второй уровень вариаций."""
        by_id = {publication.id: publication for publication in publications}
        if len(by_id) != len(publications):
            raise InvalidExternalPublicationError(
                "Публикация повторяется в изменяемой структуре."
            )
        for publication in publications:
            if publication.parent_id is None:
                continue
            parent = by_id.get(publication.parent_id)
            if (
                parent is None
                or parent.connection_id != publication.connection_id
                or parent.kind not in {PublicationKind.SIMPLE, PublicationKind.VARIABLE}
                or parent.parent_id is not None
                or (
                    required_parent_kind is not None
                    and parent.kind is not required_parent_kind
                )
            ):
                raise InvalidExternalPublicationError(
                    "Некорректный родитель разновидности."
                )
