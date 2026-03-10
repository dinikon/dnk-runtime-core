from dataclasses import dataclass, field

from src.modules.crm.domain.error import (
    ContactPointTypeAlreadyExistsError,
    ContactPointTypeInactiveError,
    ContactPointTypeNotFoundError,
    ContactPointTypeSystemLockedError,
)
from src.modules.crm.domain.contact_point.value_objects import (
    ContactPointKindVO,
    ContactPointTypeCodeVO,
    ContactPointTypeVO,
)


@dataclass(slots=True)
class ContactPointTypeDictionaryEntity:
    items: list[ContactPointTypeVO] = field(default_factory=list)

    def add_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
        title: str,
        is_system: bool = False,
        is_active: bool = True,
        sort_order: int = 0,
    ) -> ContactPointTypeVO:
        if self._find_index(kind=kind, code=code) is not None:
            raise ContactPointTypeAlreadyExistsError(kind.value, code.value)

        created = ContactPointTypeVO(
            kind=kind,
            code=code,
            title=title,
            is_system=is_system,
            is_active=is_active,
            sort_order=sort_order,
        )
        self.items.append(created)
        self._sort_items()
        return created

    def rename_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
        title: str,
    ) -> ContactPointTypeVO:
        index = self._require_index(kind=kind, code=code)
        current = self.items[index]
        if current.is_system:
            raise ContactPointTypeSystemLockedError(kind.value, code.value)
        updated = current.rename(title)
        self.items[index] = updated
        return updated

    def activate_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
    ) -> ContactPointTypeVO:
        index = self._require_index(kind=kind, code=code)
        updated = self.items[index].activate()
        self.items[index] = updated
        return updated

    def deactivate_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
    ) -> ContactPointTypeVO:
        index = self._require_index(kind=kind, code=code)
        current = self.items[index]
        if current.is_system:
            raise ContactPointTypeSystemLockedError(kind.value, code.value)
        updated = current.deactivate()
        self.items[index] = updated
        return updated

    def reorder_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
        sort_order: int,
    ) -> ContactPointTypeVO:
        index = self._require_index(kind=kind, code=code)
        updated = self.items[index].reorder(sort_order)
        self.items[index] = updated
        self._sort_items()
        return updated

    def remove_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
    ) -> None:
        index = self._require_index(kind=kind, code=code)
        current = self.items[index]
        if current.is_system:
            raise ContactPointTypeSystemLockedError(kind.value, code.value)
        del self.items[index]

    def get_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
    ) -> ContactPointTypeVO:
        index = self._find_index(kind=kind, code=code)
        if index is None:
            raise ContactPointTypeNotFoundError(kind.value, code.value)
        return self.items[index]

    def list_types(
        self,
        *,
        kind: ContactPointKindVO | None = None,
        active_only: bool = False,
    ) -> list[ContactPointTypeVO]:
        entries = self.items
        if kind is not None:
            entries = [item for item in entries if item.kind == kind]
        if active_only:
            entries = [item for item in entries if item.is_active]
        return sorted(
            entries,
            key=lambda item: (item.kind.value, item.sort_order, item.title),
        )

    def ensure_active_type(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
    ) -> None:
        item = self.get_type(kind=kind, code=code)
        if not item.is_active:
            raise ContactPointTypeInactiveError(kind.value, code.value)

    def _find_index(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
    ) -> int | None:
        for index, item in enumerate(self.items):
            if item.kind == kind and item.code == code:
                return index
        return None

    def _require_index(
        self,
        *,
        kind: ContactPointKindVO,
        code: ContactPointTypeCodeVO,
    ) -> int:
        index = self._find_index(kind=kind, code=code)
        if index is None:
            raise ContactPointTypeNotFoundError(kind.value, code.value)
        return index

    def _sort_items(self) -> None:
        self.items.sort(
            key=lambda item: (
                item.kind.value,
                item.sort_order,
                item.title,
            )
        )


__all__ = ["ContactPointTypeDictionaryEntity"]

