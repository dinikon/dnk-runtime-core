from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from ..errors import (
    FieldDefaultExceedsMaxItemsError,
    FieldDefaultOptionNotFoundError,
    FieldDefaultRelationTargetMismatchError,
    FieldDefaultTypeMismatchError,
    FieldLabelRequiredError,
    FieldOptionsNotAllowedError,
    FieldOptionsRequiredError,
    FieldRelationTargetNotAllowedError,
    FieldRelationTargetRequiredError,
    FieldSettingsTypeMismatchError,
    FieldSystemCustomFlagsInvalidError,
    FieldTimestampOrderError,
    FieldUniqueMustBeIndexedError,
)
from .configuration import (
    BooleanDefaultValue,
    DateTimeDefaultValue,
    DateTimeFieldSettings,
    FieldDefaultValue,
    FieldOptions,
    FieldSettings,
    IntegerDefaultValue,
    IntegerFieldSettings,
    JsonDefaultValue,
    JsonFieldSettings,
    MultiSelectDefaultValue,
    MultiSelectFieldOptions,
    RelationDefaultValue,
    RelationFieldSettings,
    SelectDefaultValue,
    SelectFieldOptions,
    StringDefaultValue,
    StringFieldSettings,
    UuidDefaultValue,
)
from .value_object import (
    FieldName,
    FieldIdVO,
    FieldTypeVO,
)
from ..object.value_object import ObjectIdVO
from modules.shared.domain.errors import ValidationError
from modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class FieldMetadataEntity:
    _ALLOWED_SETTINGS_BY_TYPE: ClassVar[dict[FieldTypeVO, tuple[type[object], ...]]] = {
        FieldTypeVO.UUID: tuple(),
        FieldTypeVO.STRING: (StringFieldSettings,),
        FieldTypeVO.TEXT: (StringFieldSettings,),
        FieldTypeVO.INTEGER: (IntegerFieldSettings,),
        FieldTypeVO.BOOLEAN: tuple(),
        FieldTypeVO.DATE_TIME: (DateTimeFieldSettings,),
        FieldTypeVO.JSON: (JsonFieldSettings,),
        FieldTypeVO.SELECT: tuple(),
        FieldTypeVO.MULTI_SELECT: tuple(),
        FieldTypeVO.RELATION: (RelationFieldSettings,),
    }
    _EXPECTED_DEFAULT_BY_TYPE: ClassVar[dict[FieldTypeVO, type[object]]] = {
        FieldTypeVO.UUID: UuidDefaultValue,
        FieldTypeVO.STRING: StringDefaultValue,
        FieldTypeVO.TEXT: StringDefaultValue,
        FieldTypeVO.INTEGER: IntegerDefaultValue,
        FieldTypeVO.BOOLEAN: BooleanDefaultValue,
        FieldTypeVO.DATE_TIME: DateTimeDefaultValue,
        FieldTypeVO.JSON: JsonDefaultValue,
        FieldTypeVO.SELECT: SelectDefaultValue,
        FieldTypeVO.MULTI_SELECT: MultiSelectDefaultValue,
        FieldTypeVO.RELATION: RelationDefaultValue,
    }

    id: FieldIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO
    object_metadata_id: ObjectIdVO

    field_type: FieldTypeVO
    field_name: FieldName

    label: str
    description: str | None
    icon: str | None

    is_system: bool
    is_custom: bool
    is_active: bool

    is_unique: bool
    is_index: bool
    is_nullable: bool

    is_ui_read_only: bool
    is_searchable: bool

    options: FieldOptions | None
    settings: FieldSettings | None
    default_value: FieldDefaultValue | None

    relation_target_object_id: ObjectIdVO | None
    relation_target_field_id: FieldIdVO | None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: EntityIdVO,
        object_metadata_id: ObjectIdVO,
        field_type: FieldTypeVO,
        field_name: FieldName,
        label: str,
        is_system: bool,
        is_custom: bool,
        description: str | None = None,
        icon: str | None = None,
        is_active: bool = True,
        is_unique: bool = False,
        is_index: bool = False,
        is_nullable: bool = True,
        is_ui_read_only: bool = False,
        is_searchable: bool = False,
        options: FieldOptions | None = None,
        settings: FieldSettings | None = None,
        default_value: FieldDefaultValue | None = None,
        relation_target_object_id: ObjectIdVO | None = None,
        relation_target_field_id: FieldIdVO | None = None,
        field_id: FieldIdVO | None = None,
        created_at: datetime | None = None,
    ) -> "FieldMetadataEntity":
        now = created_at or datetime.now(UTC)
        return cls(
            id=field_id or FieldIdVO.new(),
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            object_metadata_id=object_metadata_id,
            field_type=field_type,
            field_name=field_name,
            label=label,
            description=description,
            icon=icon,
            is_system=is_system,
            is_custom=is_custom,
            is_active=is_active,
            is_unique=is_unique,
            is_index=is_index,
            is_nullable=is_nullable,
            is_ui_read_only=is_ui_read_only,
            is_searchable=is_searchable,
            options=options,
            settings=settings,
            default_value=default_value,
            relation_target_object_id=relation_target_object_id,
            relation_target_field_id=relation_target_field_id,
        )

    def __post_init__(self) -> None:
        self._normalize_strings()
        self._validate_timestamps()
        self._validate_flags()
        self._validate_relation_contract()
        self._validate_options_contract()
        self._validate_settings_contract()
        self._validate_default_contract()

    def touch(self, changed_at: datetime | None = None) -> None:
        self.updated_at = changed_at or datetime.now(UTC)

    def set_options(self, options: FieldOptions | None) -> None:
        previous_value = self.options
        self.options = options
        try:
            self._validate_options_contract()
            self._validate_default_contract()
        except ValidationError:
            self.options = previous_value
            raise
        self.touch()

    def set_settings(self, settings: FieldSettings | None) -> None:
        previous_value = self.settings
        self.settings = settings
        try:
            self._validate_settings_contract()
        except ValidationError:
            self.settings = previous_value
            raise
        self.touch()

    def set_default_value(self, default_value: FieldDefaultValue | None) -> None:
        previous_value = self.default_value
        self.default_value = default_value
        try:
            self._validate_default_contract()
        except ValidationError:
            self.default_value = previous_value
            raise
        self.touch()

    def set_relation_target(
        self,
        *,
        target_object_id: ObjectIdVO | None,
        target_field_id: FieldIdVO | None = None,
    ) -> None:
        previous_object_id = self.relation_target_object_id
        previous_field_id = self.relation_target_field_id
        self.relation_target_object_id = target_object_id
        self.relation_target_field_id = target_field_id
        try:
            self._validate_relation_contract()
            self._validate_default_contract()
        except ValidationError:
            self.relation_target_object_id = previous_object_id
            self.relation_target_field_id = previous_field_id
            raise
        self.touch()

    def _normalize_strings(self) -> None:
        normalized_label = self.label.strip()
        if not normalized_label:
            raise FieldLabelRequiredError()
        self.label = normalized_label

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

    def _validate_timestamps(self) -> None:
        if self.updated_at < self.created_at:
            raise FieldTimestampOrderError()

    def _validate_flags(self) -> None:
        if self.is_system == self.is_custom:
            raise FieldSystemCustomFlagsInvalidError()
        if self.is_unique and not self.is_index:
            raise FieldUniqueMustBeIndexedError()

    def _validate_relation_contract(self) -> None:
        if self.field_type == FieldTypeVO.RELATION:
            if self.relation_target_object_id is None:
                raise FieldRelationTargetRequiredError()
            return

        if (
            self.relation_target_object_id is not None
            or self.relation_target_field_id is not None
        ):
            raise FieldRelationTargetNotAllowedError(self.field_type.value)

    def _validate_options_contract(self) -> None:
        if self.field_type == FieldTypeVO.SELECT:
            if not isinstance(self.options, SelectFieldOptions):
                raise FieldOptionsRequiredError(
                    self.field_type.value,
                    SelectFieldOptions.__name__,
                )
            return

        if self.field_type == FieldTypeVO.MULTI_SELECT:
            if not isinstance(self.options, MultiSelectFieldOptions):
                raise FieldOptionsRequiredError(
                    self.field_type.value,
                    MultiSelectFieldOptions.__name__,
                )
            return

        if self.options is not None:
            raise FieldOptionsNotAllowedError(self.field_type.value)

    def _validate_settings_contract(self) -> None:
        allowed_settings = self._ALLOWED_SETTINGS_BY_TYPE[self.field_type]
        if self.settings is None:
            return

        if not allowed_settings:
            raise FieldSettingsTypeMismatchError(
                self.field_type.value,
                "None",
                type(self.settings).__name__,
            )

        if not isinstance(self.settings, allowed_settings):
            expected_name = " | ".join(
                setting_type.__name__ for setting_type in allowed_settings
            )
            raise FieldSettingsTypeMismatchError(
                self.field_type.value,
                expected_name,
                type(self.settings).__name__,
            )

    def _validate_default_contract(self) -> None:
        if self.default_value is None:
            return

        expected_default_type = self._EXPECTED_DEFAULT_BY_TYPE[self.field_type]
        if not isinstance(self.default_value, expected_default_type):
            raise FieldDefaultTypeMismatchError(
                self.field_type.value,
                expected_default_type.__name__,
                type(self.default_value).__name__,
            )

        if self.field_type == FieldTypeVO.SELECT:
            assert isinstance(self.options, SelectFieldOptions)
            assert isinstance(self.default_value, SelectDefaultValue)
            if not self.options.contains(self.default_value.code):
                raise FieldDefaultOptionNotFoundError(self.default_value.code)
            return

        if self.field_type == FieldTypeVO.MULTI_SELECT:
            assert isinstance(self.options, MultiSelectFieldOptions)
            assert isinstance(self.default_value, MultiSelectDefaultValue)
            for code in self.default_value.codes:
                if not self.options.contains(code):
                    raise FieldDefaultOptionNotFoundError(code)
            if (
                self.options.max_items is not None
                and len(self.default_value.codes) > self.options.max_items
            ):
                raise FieldDefaultExceedsMaxItemsError(
                    max_items=self.options.max_items,
                    got=len(self.default_value.codes),
                )
            return

        if self.field_type == FieldTypeVO.RELATION:
            assert isinstance(self.default_value, RelationDefaultValue)
            if (
                self.default_value.target_object_id != self.relation_target_object_id
                or self.default_value.target_field_id != self.relation_target_field_id
            ):
                raise FieldDefaultRelationTargetMismatchError()


__all__ = ["FieldMetadataEntity"]
