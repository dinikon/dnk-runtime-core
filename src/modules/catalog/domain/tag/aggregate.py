from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.value_object.label import CatalogLabelVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


@dataclass(slots=True)
class Tag:
    """Самостоятельный справочник tag с локализованными подписями и аудитом."""

    id: TagIdVO
    translations: dict[str, str]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        identifier: TagIdVO,
        locale: LocaleVO,
        label: str,
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт новый корень с явным первоначальным переводом."""
        return cls.restore(
            identifier=identifier,
            translations={locale.value: label},
            revision=1,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: TagIdVO,
        translations: dict[str, str],
        revision: int,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Восстанавливает корень без скрытого исправления состояния."""
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise InvalidCatalogValueError("Некорректная ревизия.")
        labels = {
            LocaleVO(k).value: CatalogLabelVO(v).value for k, v in translations.items()
        }
        return cls(
            identifier, labels, revision, created_at, updated_at, created_by, updated_by
        )

    def put_translation(
        self, locale: LocaleVO, label: str, actor: EntityIdVO, now: datetime
    ) -> None:
        """Сохраняет один перевод, оставляя остальные локали."""
        value = CatalogLabelVO(label).value
        self.translations[locale.value] = value
        self._touch(actor, now)

    def ensure_revision(self, expected: int) -> None:
        """Отклоняет изменение из устаревшего редактора."""
        if expected != self.revision:
            raise CatalogConflictError(
                "Ревизия изменилась. Загрузите актуальное состояние."
            )

    def ensure_deletable(self, used: bool) -> None:
        """Защищает используемый справочник и дочерние категории от удаления."""
        if used:
            raise CatalogConflictError("Метка используется товарами.")

    def _touch(self, actor: EntityIdVO, now: datetime) -> None:
        """Фиксирует автора и новую ревизию изменения."""
        self.revision += 1
        self.updated_by = actor
        self.updated_at = now
