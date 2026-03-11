from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..errors import (
    ObjectSystemCustomFlagsInvalidError,
    ObjectTimestampOrderError,
)
from .value_object import (
    ObjectIdVO,
    ObjectLabelVO,
    ObjectNameVO,
)
from ..source.value_object import DataSourceIdVO
from modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ObjectMetadataEntity:
    id: ObjectIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO
    data_source_id: DataSourceIdVO

    object_name: ObjectNameVO
    object_label: ObjectLabelVO

    description: str | None
    icon: str | None
    shortcut: str | None

    is_remote: bool
    is_system: bool
    is_custom: bool
    is_active: bool
    is_ui_read_only: bool

    duplicate_criteria: dict[str, object] | None = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        object_name: ObjectNameVO,
        object_label: ObjectLabelVO | None = None,
        description: str | None = None,
        icon: str | None = None,
        shortcut: str | None = None,
        is_remote: bool = False,
        is_system: bool,
        is_custom: bool,
        is_active: bool = True,
        is_ui_read_only: bool = False,
        duplicate_criteria: dict[str, object] | None = None,
        object_id: ObjectIdVO | None = None,
        created_at: datetime | None = None,
    ) -> "ObjectMetadataEntity":
        now = created_at or datetime.now(UTC)
        return cls(
            id=object_id or ObjectIdVO.new(),
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            object_name=object_name,
            object_label=object_label or ObjectLabelVO.from_name(object_name),
            description=description,
            icon=icon,
            shortcut=shortcut,
            is_remote=is_remote,
            is_system=is_system,
            is_custom=is_custom,
            is_active=is_active,
            is_ui_read_only=is_ui_read_only,
            duplicate_criteria=duplicate_criteria or {},
        )

    def __post_init__(self) -> None:
        self._normalize_strings()
        self._validate_timestamps()
        self._validate_flags()
        if self.duplicate_criteria is None:
            self.duplicate_criteria = {}

    def touch(self, changed_at: datetime | None = None) -> None:
        self.updated_at = changed_at or datetime.now(UTC)

    def rename(
        self,
        *,
        object_name: ObjectNameVO,
        object_label: ObjectLabelVO | None = None,
    ) -> None:
        self.object_name = object_name
        self.object_label = object_label or ObjectLabelVO.from_name(object_name)
        self.touch()

    def activate(self) -> None:
        self.is_active = True
        self.touch()

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def _normalize_strings(self) -> None:
        normalized_description = (
            self.description.strip() if self.description is not None else None
        )
        if normalized_description == "":
            normalized_description = None
        self.description = normalized_description

        normalized_icon = self.icon.strip() if self.icon is not None else None
        if normalized_icon == "":
            normalized_icon = None
        self.icon = normalized_icon

        normalized_shortcut = self.shortcut.strip() if self.shortcut is not None else None
        if normalized_shortcut == "":
            normalized_shortcut = None
        self.shortcut = normalized_shortcut

    def _validate_timestamps(self) -> None:
        if self.updated_at < self.created_at:
            raise ObjectTimestampOrderError()

    def _validate_flags(self) -> None:
        if self.is_system == self.is_custom:
            raise ObjectSystemCustomFlagsInvalidError()


__all__ = ["ObjectMetadataEntity"]
