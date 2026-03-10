from dataclasses import dataclass, field

from src.modules.crm.domain.error import (
    ContactPointTypeAlreadyExistsError,
    ContactPointTypeInactiveError,
    ContactPointTypeNotFoundError,
    ContactPointTypeSystemLockedError,
    ContactPointValueRequiredError,
)
from src.modules.crm.domain.contact_point.value_objects import (
    ContactPointId,
    ContactPointKind,
    ContactPointType,
    ContactPointTypeCode,
)


@dataclass(slots=True)
class ContactPoint:
    id: ContactPointId
    kind: ContactPointKind
    value: str
    type_code: ContactPointTypeCode
    is_primary: bool = False
    is_verified: bool = False
    sort_order: int = 0
    is_active: bool = True

    @classmethod
    def create(
        cls,
        *,
        kind: ContactPointKind,
        value: str,
        type_code: ContactPointTypeCode,
        is_primary: bool = False,
        is_verified: bool = False,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> "ContactPoint":
        normalized_value = value.strip()
        if not normalized_value:
            raise ContactPointValueRequiredError()

        return cls(
            id=ContactPointId.new(),
            kind=kind,
            value=normalized_value,
            type_code=type_code,
            is_primary=is_primary,
            is_verified=is_verified,
            sort_order=sort_order,
            is_active=is_active,
        )

    def change_value(self, new_value: str) -> None:
        normalized_value = new_value.strip()
        if not normalized_value:
            raise ContactPointValueRequiredError()
        self.value = normalized_value

    def change_type(self, new_type_code: ContactPointTypeCode) -> None:
        self.type_code = new_type_code

    def mark_as_primary(self) -> None:
        self.is_primary = True

    def unmark_as_primary(self) -> None:
        self.is_primary = False

    def verify(self) -> None:
        self.is_verified = True

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass(slots=True)
class ContactPointTypeDictionary:
    items: list[ContactPointType] = field(default_factory=list)

    def add_type(
        self,
        *,
        kind: ContactPointKind,
        code: ContactPointTypeCode,
        title: str,
        is_system: bool = False,
        is_active: bool = True,
        sort_order: int = 0,
    ) -> ContactPointType:
        if self._find_index(kind=kind, code=code) is not None:
            raise ContactPointTypeAlreadyExistsError(kind.value, code.value)

        created = ContactPointType(
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
        kind: ContactPointKind,
        code: ContactPointTypeCode,
        title: str,
    ) -> ContactPointType:
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
        kind: ContactPointKind,
        code: ContactPointTypeCode,
    ) -> ContactPointType:
        index = self._require_index(kind=kind, code=code)
        updated = self.items[index].activate()
        self.items[index] = updated
        return updated

    def deactivate_type(
        self,
        *,
        kind: ContactPointKind,
        code: ContactPointTypeCode,
    ) -> ContactPointType:
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
        kind: ContactPointKind,
        code: ContactPointTypeCode,
        sort_order: int,
    ) -> ContactPointType:
        index = self._require_index(kind=kind, code=code)
        updated = self.items[index].reorder(sort_order)
        self.items[index] = updated
        self._sort_items()
        return updated

    def remove_type(
        self,
        *,
        kind: ContactPointKind,
        code: ContactPointTypeCode,
    ) -> None:
        index = self._require_index(kind=kind, code=code)
        current = self.items[index]
        if current.is_system:
            raise ContactPointTypeSystemLockedError(kind.value, code.value)
        del self.items[index]

    def get_type(
        self,
        *,
        kind: ContactPointKind,
        code: ContactPointTypeCode,
    ) -> ContactPointType:
        index = self._find_index(kind=kind, code=code)
        if index is None:
            raise ContactPointTypeNotFoundError(kind.value, code.value)
        return self.items[index]

    def list_types(
        self,
        *,
        kind: ContactPointKind | None = None,
        active_only: bool = False,
    ) -> list[ContactPointType]:
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
        kind: ContactPointKind,
        code: ContactPointTypeCode,
    ) -> None:
        item = self.get_type(kind=kind, code=code)
        if not item.is_active:
            raise ContactPointTypeInactiveError(kind.value, code.value)

    def _find_index(
        self,
        *,
        kind: ContactPointKind,
        code: ContactPointTypeCode,
    ) -> int | None:
        for index, item in enumerate(self.items):
            if item.kind == kind and item.code == code:
                return index
        return None

    def _require_index(
        self,
        *,
        kind: ContactPointKind,
        code: ContactPointTypeCode,
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
