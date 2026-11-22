from src.modules.feed_builder.domain.publication.value_object.feed_publication_version import (
    FeedPublicationVersionVO,
)
from src.modules.feed_builder.domain.publication.error import PublicationTransitionError
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus,
)
from src.modules.feed_builder.domain.publication.error import (
    DuplicateFieldOverrideError,
    InvalidPublicationValueError,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.validation import require_datetime


@dataclass(frozen=True, slots=True)
class FeedPublication:
    """Корневой агрегат участия одной продаваемой позиции Catalog в фиде."""

    id: FeedPublicationIdVO
    feed_id: FeedIdVO
    product_reference: CatalogProductReferenceVO
    status: PublicationStatus
    overrides: tuple[FieldOverrideVO, ...]
    created_at: datetime
    updated_at: datetime
    version: FeedPublicationVersionVO

    @classmethod
    def create(
        cls,
        *,
        identifier: FeedPublicationIdVO,
        feed_id: FeedIdVO,
        product_reference: CatalogProductReferenceVO,
        now: datetime,
    ) -> Self:
        """Создаёт ENABLED-публикацию без ручных значений и без обращения к Catalog."""
        return cls.restore(
            identifier=identifier,
            feed_id=feed_id,
            product_reference=product_reference,
            status=PublicationStatus.ENABLED,
            overrides=(),
            created_at=now,
            updated_at=now,
            version=FeedPublicationVersionVO(1),
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FeedPublicationIdVO,
        feed_id: FeedIdVO,
        product_reference: CatalogProductReferenceVO,
        status: PublicationStatus,
        overrides: tuple[FieldOverrideVO, ...],
        created_at: datetime,
        updated_at: datetime,
        version: FeedPublicationVersionVO,
    ) -> Self:
        """Восстанавливает состояние, проверяя уникальность overrides и собственные даты."""
        if (
            not isinstance(identifier, FeedPublicationIdVO)
            or not isinstance(feed_id, FeedIdVO)
            or not isinstance(product_reference, CatalogProductReferenceVO)
            or not isinstance(version, FeedPublicationVersionVO)
            or not isinstance(status, PublicationStatus)
            or not isinstance(overrides, (list, tuple))
            or len(overrides) > MAX_FIELDS
        ):
            raise InvalidPublicationValueError(
                "Нужны типизированные свойства публикации."
            )
        require_datetime(created_at, error=InvalidPublicationValueError)
        require_datetime(updated_at, error=InvalidPublicationValueError)
        if updated_at < created_at:
            raise InvalidPublicationValueError(
                "Изменение предшествует созданию публикации."
            )
        identifiers: set[FieldIdVO] = set()
        for index, override in enumerate(overrides):
            if not isinstance(override, FieldOverrideVO):
                raise InvalidPublicationValueError("Нужен FieldOverrideVO.")
            if override.field_id in identifiers:
                raise DuplicateFieldOverrideError(
                    "Ручное значение поля повторяется.",
                    path=("overrides", index, "field_id"),
                )
            identifiers.add(override.field_id)
        return cls(
            id=identifier,
            feed_id=feed_id,
            product_reference=product_reference,
            status=status,
            overrides=tuple(overrides),
            created_at=created_at,
            updated_at=updated_at,
            version=version,
        )

    def _transition(
        self,
        target: PublicationStatus,
        allowed: tuple[PublicationStatus, ...],
        now: datetime,
    ) -> Self:
        """Атомарно меняет участие, сохраняя ссылку, overrides и исходную дату."""
        require_datetime(now, error=InvalidPublicationValueError)
        if now < self.updated_at:
            raise InvalidPublicationValueError(
                "Время изменения не может двигаться назад."
            )
        if self.status is target:
            return self
        if self.status not in allowed:
            raise PublicationTransitionError(
                "Недопустимое изменение участия публикации."
            )
        return replace(
            self,
            status=target,
            updated_at=now,
            version=FeedPublicationVersionVO(self.version.value + 1),
        )

    def enable(self, *, now: datetime) -> Self:
        """Возобновляет участие без восстановления архивной публикации."""
        return self._transition(
            PublicationStatus.ENABLED,
            (PublicationStatus.PAUSED, PublicationStatus.DRAFT),
            now,
        )

    def pause(self, *, now: datetime) -> Self:
        """Приостанавливает участвующую позицию без изменения Catalog."""
        return self._transition(
            PublicationStatus.PAUSED, (PublicationStatus.ENABLED,), now
        )

    def archive(self, *, now: datetime) -> Self:
        """Убирает позицию из состава, сохраняя идентичность и ручные значения."""
        return self._transition(
            PublicationStatus.ARCHIVED,
            (
                PublicationStatus.ENABLED,
                PublicationStatus.PAUSED,
                PublicationStatus.DRAFT,
            ),
            now,
        )

    def restore_participation(self, *, now: datetime) -> Self:
        """Явно возвращает архивную позицию в состав фида."""
        return self._transition(
            PublicationStatus.ENABLED, (PublicationStatus.ARCHIVED,), now
        )
