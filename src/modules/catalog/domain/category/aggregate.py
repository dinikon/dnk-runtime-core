from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.value_object.label import CatalogLabelVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


@dataclass(slots=True)
class Category:
    """Самостоятельный справочник category с локализованными подписями и аудитом."""

    id: CategoryIdVO
    parent_id: CategoryIdVO | None
    translations: dict[str, str]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        identifier: CategoryIdVO,
        parent_id: CategoryIdVO | None,
        ancestors: frozenset[CategoryIdVO],
        locale: LocaleVO,
        label: str,
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт новый корень с явным первоначальным переводом."""
        cls._validate_parent(identifier, parent_id, ancestors)
        return cls.restore(
            identifier=identifier,
            parent_id=parent_id,
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
        identifier: CategoryIdVO,
        parent_id: CategoryIdVO | None,
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
        cls._validate_parent(identifier, parent_id, frozenset())
        labels = {
            LocaleVO(k).value: CatalogLabelVO(v).value for k, v in translations.items()
        }
        return cls(
            identifier,
            parent_id,
            labels,
            revision,
            created_at,
            updated_at,
            created_by,
            updated_by,
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
            raise CatalogConflictError(
                "Объект используется товарами или имеет дочерние категории."
            )

    def _touch(self, actor: EntityIdVO, now: datetime) -> None:
        """Фиксирует автора и новую ревизию изменения."""
        self.revision += 1
        self.updated_by = actor
        self.updated_at = now

    @staticmethod
    def _validate_parent(
        identifier: CategoryIdVO,
        parent_id: CategoryIdVO | None,
        ancestors: frozenset[CategoryIdVO],
    ) -> None:
        """Запрещает ссылку на себя и перемещение под своего потомка."""
        if parent_id == identifier or identifier in ancestors:
            raise InvalidCatalogValueError("Дерево категорий не допускает циклов.")

    def move(
        self,
        parent_id: CategoryIdVO | None,
        ancestors: frozenset[CategoryIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет место в дереве по проверенному снимку предков нового родителя."""
        self._validate_parent(self.id, parent_id, ancestors)
        self.parent_id = parent_id
        self._touch(actor, now)
