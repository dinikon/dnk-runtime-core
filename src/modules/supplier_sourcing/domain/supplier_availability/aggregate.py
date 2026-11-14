from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Self

from src.modules.supplier_sourcing.domain.supplier_availability.error import (
    InvalidSupplierAvailabilityValueError,
    SupplierAvailabilityContextMismatchError,
    SupplierAvailabilityTimeError,
    SupplierAvailabilityVersionConflictError,
)
from src.modules.supplier_sourcing.domain.supplier_availability.evaluation import (
    SupplierAvailabilityEvaluation,
)
from src.modules.supplier_sourcing.domain.supplier_availability.value_object.identifier import (
    SupplierAvailabilityIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_availability.value_object.observation import (
    AvailabilityStatus,
    AvailabilityType,
    SupplierAvailabilityObservationVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.availability_snapshot import (
    SupplierOfferAvailabilitySnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.identifier import (
    SupplierOfferIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.uom_code import (
    SupplierOfferUomCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.availability_snapshot import (
    SupplierSourceAvailabilitySnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior,
)


@dataclass(frozen=True, slots=True)
class SupplierAvailability:
    """Хранит последнее принятое наблюдение пары предложения и источника."""

    id: SupplierAvailabilityIdVO
    supplier_offer_id: SupplierOfferIdVO
    supplier_source_id: SupplierSourceIdVO
    base_uom: SupplierOfferUomCodeVO
    observation: SupplierAvailabilityObservationVO
    source_updated_at: datetime | None
    received_at: datetime
    expires_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: SupplierAvailabilityIdVO,
        offer: SupplierOfferAvailabilitySnapshot,
        source: SupplierSourceAvailabilitySnapshot,
        observation: SupplierAvailabilityObservationVO,
        uom: SupplierOfferUomCodeVO,
        received_at: datetime,
        source_updated_at: datetime | None = None,
    ) -> Self:
        """Фиксирует первое наблюдение совместимых предложения и источника с версией ноль."""
        cls._ensure_context(offer=offer, source=source, uom=uom)
        received = cls._normalize_time(received_at)
        return cls.restore(
            identifier=identifier,
            supplier_offer_id=offer.id,
            supplier_source_id=source.identity.id,
            base_uom=offer.base_uom,
            observation=observation,
            source_updated_at=source_updated_at,
            received_at=received,
            expires_at=cls._expiration(received, source),
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: SupplierAvailabilityIdVO,
        supplier_offer_id: SupplierOfferIdVO,
        supplier_source_id: SupplierSourceIdVO,
        base_uom: SupplierOfferUomCodeVO,
        observation: SupplierAvailabilityObservationVO,
        source_updated_at: datetime | None,
        received_at: datetime,
        expires_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает собственное состояние с сохранённым сроком действия."""
        availability = cls(
            id=identifier,
            supplier_offer_id=supplier_offer_id,
            supplier_source_id=supplier_source_id,
            base_uom=base_uom,
            observation=observation,
            source_updated_at=(
                cls._normalize_time(source_updated_at)
                if source_updated_at is not None
                else None
            ),
            received_at=cls._normalize_time(received_at),
            expires_at=cls._normalize_time(expires_at),
            version=version,
        )
        availability._validate()
        return availability

    def record_observation(
        self,
        *,
        offer: SupplierOfferAvailabilitySnapshot,
        source: SupplierSourceAvailabilitySnapshot,
        observation: SupplierAvailabilityObservationVO,
        uom: SupplierOfferUomCodeVO,
        received_at: datetime,
        expected_version: int,
        source_updated_at: datetime | None = None,
    ) -> Self:
        """Применяет новое наблюдение для той же пары, сохраняя точный повтор без изменений."""
        self._validate()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidSupplierAvailabilityValueError(
                "Ожидаемая версия должна быть целым числом от нуля."
            )
        if expected_version != self.version:
            raise SupplierAvailabilityVersionConflictError(
                "Версия наблюдения уже изменилась."
            )
        self._ensure_context(offer=offer, source=source, uom=uom)
        if (offer.id, source.identity.id, uom) != (
            self.supplier_offer_id,
            self.supplier_source_id,
            self.base_uom,
        ):
            raise SupplierAvailabilityContextMismatchError(
                "Обновление должно относиться к сохранённой паре и базовой единице."
            )
        if not isinstance(observation, SupplierAvailabilityObservationVO):
            raise InvalidSupplierAvailabilityValueError(
                "Нужно типизированное наблюдение наличия."
            )
        received = self._normalize_time(received_at)
        updated = (
            self._normalize_time(source_updated_at)
            if source_updated_at is not None
            else None
        )
        if (observation, received, updated) == (
            self.observation,
            self.received_at,
            self.source_updated_at,
        ):
            return self
        self._ensure_observation_order(
            observation=observation, received_at=received, source_updated_at=updated
        )
        return replace(
            self,
            observation=observation,
            source_updated_at=updated,
            received_at=received,
            expires_at=self._expiration(received, source),
            version=self.version + 1,
        )

    def evaluate(
        self, *, as_of: datetime, source: SupplierSourceAvailabilitySnapshot
    ) -> SupplierAvailabilityEvaluation:
        """Оценивает текущее наблюдение и применяет правило устаревания его источника."""
        self._validate()
        self._ensure_source_snapshot(source)
        if source.identity.id != self.supplier_source_id:
            raise SupplierAvailabilityContextMismatchError(
                "Для оценки нужен источник сохранённого наблюдения."
            )
        at = self._normalize_time(as_of)
        if at < self.received_at:
            raise SupplierAvailabilityTimeError(
                "Текущее наблюдение доступно для оценки с момента получения."
            )
        if at < self.expires_at:
            return SupplierAvailabilityEvaluation(self.observation, False, False)
        return SupplierAvailabilityEvaluation(
            SupplierAvailabilityObservationVO(
                AvailabilityType.UNKNOWN, AvailabilityStatus.UNKNOWN, None
            ),
            is_stale=True,
            automatic_sale_blocked=(
                source.stock_update_policy.stale_behavior
                is StaleStockBehavior.BLOCK_AUTOMATIC_SALE
            ),
        )

    @classmethod
    def _ensure_context(
        cls,
        *,
        offer: SupplierOfferAvailabilitySnapshot,
        source: SupplierSourceAvailabilitySnapshot,
        uom: SupplierOfferUomCodeVO,
    ) -> None:
        """Проверяет принадлежность пары и соответствие единицы наблюдения предложению."""
        if not isinstance(offer, SupplierOfferAvailabilitySnapshot):
            raise InvalidSupplierAvailabilityValueError(
                "Нужен снимок предложения для учёта наличия."
            )
        offer.ensure_valid()
        cls._ensure_source_snapshot(source)
        if (
            offer.supplier != source.identity.supplier
            or (offer.source_id is not None and offer.source_id != source.identity.id)
            or not isinstance(uom, SupplierOfferUomCodeVO)
            or uom != offer.base_uom
        ):
            raise SupplierAvailabilityContextMismatchError(
                "Предложение и источник должны относиться к одному поставщику и совпадать по ограничению источника и единице наблюдения."
            )

    @staticmethod
    def _ensure_source_snapshot(source: SupplierSourceAvailabilitySnapshot) -> None:
        """Требует проверяемые данные источника с настройками актуальности."""
        if not isinstance(source, SupplierSourceAvailabilitySnapshot):
            raise InvalidSupplierAvailabilityValueError(
                "Нужен снимок источника с настройками актуальности."
            )
        source.ensure_valid()

    def _ensure_observation_order(
        self,
        *,
        observation: SupplierAvailabilityObservationVO,
        received_at: datetime,
        source_updated_at: datetime | None,
    ) -> None:
        """Отклоняет опоздавшие наблюдения и конфликт данных на одной отметке поставщика."""
        if received_at <= self.received_at:
            raise SupplierAvailabilityTimeError(
                "Новое наблюдение должно быть получено позже текущего."
            )
        if source_updated_at is not None and self.source_updated_at is not None:
            if source_updated_at < self.source_updated_at or (
                source_updated_at == self.source_updated_at
                and observation != self.observation
            ):
                raise SupplierAvailabilityTimeError(
                    "Отметка поставщика устарела или противоречит уже принятым данным."
                )

    def _validate(self) -> None:
        """Проверяет типизированные поля, строгую версию и сохранённую UTC-хронологию."""
        if (
            not isinstance(self.id, SupplierAvailabilityIdVO)
            or not isinstance(self.supplier_offer_id, SupplierOfferIdVO)
            or not isinstance(self.supplier_source_id, SupplierSourceIdVO)
            or not isinstance(self.base_uom, SupplierOfferUomCodeVO)
            or not isinstance(self.observation, SupplierAvailabilityObservationVO)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidSupplierAvailabilityValueError(
                "Нужны типизированные поля наблюдения и неотрицательная целая версия."
            )
        dates = (self.received_at, self.expires_at)
        if self.source_updated_at is not None:
            dates += (self.source_updated_at,)
        for value in dates:
            self._normalize_time(value)
            if value.utcoffset() != timedelta(0):
                raise SupplierAvailabilityTimeError(
                    "Времена сохранённого наблюдения должны быть в UTC."
                )
        if self.expires_at <= self.received_at:
            raise SupplierAvailabilityTimeError(
                "Срок действия наблюдения должен заканчиваться после его получения."
            )

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Переводит явно заданное время с часовым поясом в UTC."""
        if not isinstance(value, datetime):
            raise SupplierAvailabilityTimeError("Нужен datetime с часовым поясом.")
        try:
            if value.utcoffset() is None:
                raise SupplierAvailabilityTimeError("Нужен datetime с часовым поясом.")
            return value.astimezone(UTC)
        except (OverflowError, ValueError) as exc:
            raise SupplierAvailabilityTimeError(
                "Время невозможно представить в UTC."
            ) from exc

    @staticmethod
    def _expiration(
        received_at: datetime, source: SupplierSourceAvailabilitySnapshot
    ) -> datetime:
        """Вычисляет конец срока действия по моменту получения и TTL источника."""
        try:
            return received_at + source.stock_update_policy.ttl
        except OverflowError as exc:
            raise SupplierAvailabilityTimeError(
                "Срок действия наблюдения выходит за допустимый диапазон дат."
            ) from exc
