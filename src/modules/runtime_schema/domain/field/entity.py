from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from ..errors import (
    FieldDefaultExceedsMaxItemsError,
    FieldDefaultOptionNotFoundError,
    FieldDefaultRelationTargetMismatchError,
    FieldDefaultTypeMismatchError,
    FieldDefaultValueInvalidError,
    FieldLabelRequiredError,
    FieldOptionsNotAllowedError,
    FieldOptionsRequiredError,
    FieldRelationTargetNotAllowedError,
    FieldRelationTargetRequiredError,
    FieldSettingsTypeMismatchError,
    FieldTimestampOrderError,
    FieldUniqueMustBeIndexedError,
)
from .configuration import (
    ActorDefaultValue,
    ActorFieldSettings,
    AddressDefaultValue,
    AddressFieldSettings,
    ArrayDefaultValue,
    ArrayFieldSettings,
    ArrayItemTypeVO,
    BooleanDefaultValue,
    CurrencyDefaultValue,
    CurrencyFieldSettings,
    DateTimeDefaultValue,
    DateTimeFieldSettings,
    EmailsDefaultValue,
    EmailsFieldSettings,
    FieldDefaultValue,
    FieldOptions,
    FieldSettings,
    FullNameDefaultValue,
    FullNameFieldSettings,
    IntegerDefaultValue,
    IntegerFieldSettings,
    JsonDefaultValue,
    JsonFieldSettings,
    LinksDefaultValue,
    LinksFieldSettings,
    MultiSelectDefaultValue,
    MultiSelectFieldOptions,
    PhonesDefaultValue,
    PhonesFieldSettings,
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
        FieldTypeVO.ACTOR: (ActorFieldSettings,),
        FieldTypeVO.ADDRESS: (AddressFieldSettings,),
        FieldTypeVO.ARRAY: (ArrayFieldSettings,),
        FieldTypeVO.UUID: tuple(),
        FieldTypeVO.STRING: (StringFieldSettings,),
        FieldTypeVO.TEXT: (StringFieldSettings,),
        FieldTypeVO.INTEGER: (IntegerFieldSettings,),
        FieldTypeVO.BOOLEAN: tuple(),
        FieldTypeVO.CURRENCY: (CurrencyFieldSettings,),
        FieldTypeVO.DATE_TIME: (DateTimeFieldSettings,),
        FieldTypeVO.EMAILS: (EmailsFieldSettings,),
        FieldTypeVO.FULL_NAME: (FullNameFieldSettings,),
        FieldTypeVO.JSON: (JsonFieldSettings,),
        FieldTypeVO.LINKS: (LinksFieldSettings,),
        FieldTypeVO.PHONES: (PhonesFieldSettings,),
        FieldTypeVO.SELECT: tuple(),
        FieldTypeVO.MULTI_SELECT: tuple(),
        FieldTypeVO.RELATION: (RelationFieldSettings,),
    }
    _EXPECTED_DEFAULT_BY_TYPE: ClassVar[dict[FieldTypeVO, type[object]]] = {
        FieldTypeVO.ACTOR: ActorDefaultValue,
        FieldTypeVO.ADDRESS: AddressDefaultValue,
        FieldTypeVO.ARRAY: ArrayDefaultValue,
        FieldTypeVO.UUID: UuidDefaultValue,
        FieldTypeVO.STRING: StringDefaultValue,
        FieldTypeVO.TEXT: StringDefaultValue,
        FieldTypeVO.INTEGER: IntegerDefaultValue,
        FieldTypeVO.BOOLEAN: BooleanDefaultValue,
        FieldTypeVO.CURRENCY: CurrencyDefaultValue,
        FieldTypeVO.DATE_TIME: DateTimeDefaultValue,
        FieldTypeVO.EMAILS: EmailsDefaultValue,
        FieldTypeVO.FULL_NAME: FullNameDefaultValue,
        FieldTypeVO.JSON: JsonDefaultValue,
        FieldTypeVO.LINKS: LinksDefaultValue,
        FieldTypeVO.PHONES: PhonesDefaultValue,
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

    is_unique: bool
    is_index: bool
    is_nullable: bool

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
        description: str | None = None,
        icon: str | None = None,
        is_unique: bool = False,
        is_index: bool = False,
        is_nullable: bool = True,
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
            is_unique=is_unique,
            is_index=is_index,
            is_nullable=is_nullable,
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

        if self.field_type == FieldTypeVO.ADDRESS:
            assert isinstance(self.default_value, AddressDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, AddressFieldSettings)
                else AddressFieldSettings()
            )
            if settings.require_country and not self.default_value.country:
                raise FieldDefaultValueInvalidError("address country is required")
            if settings.require_region and not self.default_value.region:
                raise FieldDefaultValueInvalidError("address region is required")
            if settings.require_city and not self.default_value.city:
                raise FieldDefaultValueInvalidError("address city is required")
            if settings.require_address_line and not self.default_value.address_line:
                raise FieldDefaultValueInvalidError("address line is required")
            if settings.require_post_code and not self.default_value.post_code:
                raise FieldDefaultValueInvalidError("address post_code is required")
            return

        if self.field_type == FieldTypeVO.ARRAY:
            assert isinstance(self.default_value, ArrayDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, ArrayFieldSettings)
                else ArrayFieldSettings()
            )
            self._validate_collection_size(
                size=len(self.default_value.values),
                max_items=settings.max_items,
                field_name=self.field_type.value,
            )
            if (
                not settings.allow_duplicates
                and len(set(self.default_value.values)) != len(self.default_value.values)
            ):
                raise FieldDefaultValueInvalidError("array default contains duplicates")
            for item in self.default_value.values:
                if not self._is_array_item_valid(item=item, item_type=settings.item_type):
                    raise FieldDefaultValueInvalidError(
                        f"array item '{item}' does not match item_type '{settings.item_type.value}'"
                    )
            return

        if self.field_type == FieldTypeVO.CURRENCY:
            assert isinstance(self.default_value, CurrencyDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, CurrencyFieldSettings)
                else CurrencyFieldSettings()
            )
            if (
                settings.allowed_currencies is not None
                and self.default_value.currency not in settings.allowed_currencies
            ):
                raise FieldDefaultValueInvalidError(
                    f"currency '{self.default_value.currency}' is not allowed"
                )
            if self.default_value.display_value is not None:
                fraction_digits = self._fraction_digits(self.default_value.display_value)
                if fraction_digits > settings.display_scale:
                    raise FieldDefaultValueInvalidError(
                        f"currency display value has {fraction_digits} digits after decimal; max is {settings.display_scale}"
                    )
            return

        if self.field_type == FieldTypeVO.DATE_TIME:
            assert isinstance(self.default_value, DateTimeDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, DateTimeFieldSettings)
                else DateTimeFieldSettings()
            )
            if settings.timezone_aware and self.default_value.value.tzinfo is None:
                raise FieldDefaultValueInvalidError(
                    "date_time default must be timezone-aware"
                )
            if not settings.timezone_aware and self.default_value.value.tzinfo is not None:
                raise FieldDefaultValueInvalidError(
                    "date_time default must be naive when timezone_aware is false"
                )
            if settings.require_utc:
                offset = self.default_value.value.utcoffset()
                if offset != timedelta(0):
                    raise FieldDefaultValueInvalidError(
                        "date_time default must be normalized to UTC"
                    )
            return

        if self.field_type == FieldTypeVO.EMAILS:
            assert isinstance(self.default_value, EmailsDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, EmailsFieldSettings)
                else EmailsFieldSettings()
            )
            self._validate_collection_size(
                size=len(self.default_value.emails),
                max_items=settings.max_items,
                field_name=self.field_type.value,
            )
            if (
                not settings.allow_duplicates
                and len(set(self.default_value.emails)) != len(self.default_value.emails)
            ):
                raise FieldDefaultValueInvalidError("emails default contains duplicates")
            return

        if self.field_type == FieldTypeVO.FULL_NAME:
            assert isinstance(self.default_value, FullNameDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, FullNameFieldSettings)
                else FullNameFieldSettings()
            )
            if settings.require_last_name and not self.default_value.last_name:
                raise FieldDefaultValueInvalidError("full_name last_name is required")
            if settings.require_middle_name and not self.default_value.middle_name:
                raise FieldDefaultValueInvalidError("full_name middle_name is required")
            if settings.require_first_name and not self.default_value.first_name:
                raise FieldDefaultValueInvalidError("full_name first_name is required")
            return

        if self.field_type == FieldTypeVO.LINKS:
            assert isinstance(self.default_value, LinksDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, LinksFieldSettings)
                else LinksFieldSettings()
            )
            self._validate_collection_size(
                size=len(self.default_value.links),
                max_items=settings.max_items,
                field_name=self.field_type.value,
            )
            if (
                not settings.allow_duplicates
                and len(set(self.default_value.links)) != len(self.default_value.links)
            ):
                raise FieldDefaultValueInvalidError("links default contains duplicates")
            return

        if self.field_type == FieldTypeVO.PHONES:
            assert isinstance(self.default_value, PhonesDefaultValue)
            settings = (
                self.settings
                if isinstance(self.settings, PhonesFieldSettings)
                else PhonesFieldSettings()
            )
            self._validate_collection_size(
                size=len(self.default_value.phones),
                max_items=settings.max_items,
                field_name=self.field_type.value,
            )
            if (
                not settings.allow_duplicates
                and len(set(self.default_value.phones)) != len(self.default_value.phones)
            ):
                raise FieldDefaultValueInvalidError("phones default contains duplicates")
            return

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

    @staticmethod
    def _validate_collection_size(
        *,
        size: int,
        max_items: int | None,
        field_name: str,
    ) -> None:
        if max_items is not None and size > max_items:
            raise FieldDefaultValueInvalidError(
                f"{field_name} default contains {size} values, max is {max_items}"
            )

    @staticmethod
    def _is_array_item_valid(*, item: object, item_type: ArrayItemTypeVO) -> bool:
        if item_type == ArrayItemTypeVO.STRING:
            return isinstance(item, str)
        if item_type == ArrayItemTypeVO.INTEGER:
            return isinstance(item, int) and not isinstance(item, bool)
        if item_type == ArrayItemTypeVO.BOOLEAN:
            return isinstance(item, bool)
        if item_type == ArrayItemTypeVO.UUID:
            if isinstance(item, UUID):
                return True
            if not isinstance(item, str):
                return False
            try:
                UUID(item)
            except ValueError:
                return False
            return True
        if item_type == ArrayItemTypeVO.DATE_TIME:
            return isinstance(item, datetime)
        if item_type == ArrayItemTypeVO.NUMBER:
            return isinstance(item, (int, float, Decimal)) and not isinstance(item, bool)
        return False

    @staticmethod
    def _fraction_digits(value: str) -> int:
        if "." not in value:
            return 0
        return len(value.split(".", 1)[1])


__all__ = ["FieldMetadataEntity"]
