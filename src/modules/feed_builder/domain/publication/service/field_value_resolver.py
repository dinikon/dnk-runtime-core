from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.types import (
    ResolvedFieldValue,
    ScalarFieldType,
)
from src.modules.feed_builder.domain.feed.value_object.boolean_calculation import (
    BooleanCalculationVO,
)
from src.modules.feed_builder.domain.feed.value_object.boolean_field_type import (
    BooleanFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.constant_value_definition import (
    ConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.integer_field_type import (
    IntegerFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_field_type import (
    TextFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.calculation.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.calculation.evaluator import (
    MoneyFieldCalculator,
    calculate_boolean,
)
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.field_type_validation import (
    apply_text_transforms,
    valid_text_characters,
)
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.calculation_inputs import (
    CalculationInputsVO,
)
from src.modules.feed_builder.domain.feed.value_object.string_field_type import (
    StringFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.feed.value_object.price_value import PriceValueVO
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constant_value_definition import (
    TextConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class FieldIssue:
    """Описывает ошибку значения поля или недоступность позиции."""

    field_id: UUID | None
    code: str
    message: str
    path: tuple[str | int, ...] = ()
    rule_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ResolvedField:
    """Передаёт конечное типизированное значение и его происхождение."""

    field_id: UUID
    value: ResolvedFieldValue
    origin: str
    actual_locale: str | None = None
    issues: tuple[FieldIssue, ...] = ()


class FieldValueResolver:
    """Подготавливает значение одного поля без доступа к Catalog или часам."""

    def resolve_manual(
        self, field: FieldDefinition, override: FieldOverrideVO, product_id: EntityIdVO
    ) -> ResolvedField:
        """Подготавливает ручное значение без загрузки исходных данных."""
        settings, value = field.type_definition, override.value
        if isinstance(value, str) and isinstance(
            settings, (StringFieldTypeVO, TextFieldTypeVO)
        ):
            if not valid_text_characters(
                value, multiline=isinstance(settings, TextFieldTypeVO)
            ):
                return self._issue(
                    field,
                    "MANUAL",
                    "INVALID_FIELD_VALUE",
                    "Недопустимые символы для этого текстового поля.",
                )
            maximum = settings.constraints.max_length
            if maximum is not None and len(value) > maximum:
                return self._issue(
                    field,
                    "MANUAL",
                    "TEXT_LENGTH_CONSTRAINT",
                    f"Допустимо не более {maximum} символов.",
                )
        return self.resolve(
            field,
            PublicationCatalogSnapshotVO(
                CalculationInputsVO(product_id, None, None, None, None), ()
            ),
            override,
        )

    def resolve(
        self,
        field: FieldDefinition,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Выбирает источник значения, затем применяет настройки указанного типа."""
        settings = field.type_definition
        if isinstance(settings, MoneyFieldTypeVO):
            return self._money(field, settings, snapshot, override)
        if isinstance(settings, (IntegerFieldTypeVO, BooleanFieldTypeVO)):
            return self._scalar(field, settings, snapshot, override)

        definition = settings.value_definition
        locale = None
        manual_translation = False
        if override is not None:
            value = override.value
            origin = "MANUAL"
        elif isinstance(definition, TextConstantValueDefinitionVO):
            value = definition.value
            origin = "CONSTANT"
        elif not isinstance(definition, SourceValueDefinitionVO):
            value = None
            origin = "MANUAL"
        elif definition.source.path is CatalogSourcePath.SKU:
            value = snapshot.inputs.sku
            origin = "INHERITED"
        else:
            origin = "INHERITED"
            value = None
            fallback = settings.fallback_policy
            locales = (
                (settings.locale.value, *(code.value for code in fallback.locales))
                if settings.locale is not None and fallback is not None
                else (settings.locale.value,) if settings.locale is not None else ()
            )
            for candidate in locales:
                value = snapshot.text(definition.source.path.value, candidate)
                if value not in (None, ""):
                    locale = candidate
                    break
            manual_translation = (
                value in (None, "")
                and fallback is not None
                and fallback.mode is LocaleFallbackMode.MANUAL_REQUIRED
            )

        if value is not None and not isinstance(value, str):
            return self._issue(field, origin, "INVALID_FIELD_VALUE", "Ожидается текст.")
        if value is not None:
            value = apply_text_transforms(value, settings.transforms)
        constraints = settings.constraints
        if manual_translation or (
            constraints.required and (value is None or not value.strip())
        ):
            return self._issue(
                field, origin, "REQUIRED_VALUE_MISSING", "Требуется значение поля."
            )
        if value is not None and not constraints.accepts_length(value):
            return self._issue(
                field, origin, "TEXT_LENGTH_CONSTRAINT", "Длина текста вне границ поля."
            )
        return ResolvedField(field.id.uuid, value, origin, locale)

    def _scalar(
        self,
        field: FieldDefinition,
        settings: ScalarFieldType,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Разрешает числовые и логические поля без подмены нуля и false."""
        definition = settings.value_definition
        if override is not None:
            value, origin = override.value, "MANUAL"
        elif isinstance(definition, ConstantValueDefinitionVO):
            value, origin = definition.value, "CONSTANT"
        elif isinstance(definition, SourceValueDefinitionVO):
            value = (
                snapshot.inputs.stock_quantity
                if definition.source.path is CatalogSourcePath.STOCK_QUANTITY
                else snapshot.inputs.in_stock
            )
            origin = "INHERITED"
        elif isinstance(definition, BooleanCalculationVO):
            result = calculate_boolean(definition, snapshot.inputs)
            if result.issues:
                return ResolvedField(
                    field.id.uuid,
                    None,
                    "CALCULATED",
                    issues=tuple(
                        FieldIssue(field.id.uuid, issue.code, issue.message, issue.path)
                        for issue in result.issues
                    ),
                )
            value, origin = result.value, "CALCULATED"
        else:
            value, origin = None, "MANUAL"
        if value is None:
            if settings.required:
                return self._issue(
                    field, origin, "REQUIRED_VALUE_MISSING", "Требуется значение поля."
                )
        elif isinstance(settings, IntegerFieldTypeVO) and not settings.accepts(value):
            return self._issue(
                field,
                origin,
                "INVALID_INTEGER_VALUE",
                "Нужно целое число в допустимых границах поля.",
            )
        elif isinstance(settings, BooleanFieldTypeVO) and type(value) is not bool:
            return self._issue(
                field, origin, "INVALID_BOOLEAN_VALUE", "Ожидается true или false."
            )
        return ResolvedField(field.id.uuid, value, origin)

    def _money(
        self,
        field: FieldDefinition,
        settings: MoneyFieldTypeVO,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Переиспользует денежный вычислитель и его финальные преобразования."""
        mode = settings.value_definition.mode
        manual = override is not None or mode is MoneyValueMode.MANUAL
        origin = (
            "MANUAL"
            if manual
            else "CALCULATED" if mode is MoneyValueMode.CALCULATED else "INHERITED"
        )
        missing = (
            (override is None or override.value is None)
            if manual
            else mode is MoneyValueMode.SOURCE and snapshot.inputs.regular is None
        )
        if missing:
            if settings.constraints.required:
                return self._issue(
                    field, origin, "REQUIRED_VALUE_MISSING", "Требуется значение поля."
                )
            return ResolvedField(field.id.uuid, None, origin)
        if override is not None and not isinstance(override.value, PriceAmountVO):
            return self._issue(
                field, origin, "INVALID_FIELD_VALUE", "Ожидается денежная сумма."
            )
        try:
            result = MoneyFieldCalculator.calculate(
                field,
                snapshot.inputs,
                manual_amount=override.value if override is not None else None,
            )
        except CalculationDefinitionError as exc:
            return ResolvedField(
                field.id.uuid,
                None,
                origin,
                issues=(FieldIssue(field.id.uuid, exc.code, str(exc), exc.path),),
            )
        return ResolvedField(
            field.id.uuid,
            result.value,
            origin,
            issues=tuple(
                FieldIssue(
                    field.id.uuid, issue.code, issue.message, issue.path, issue.rule_id
                )
                for issue in result.issues
            ),
        )

    @staticmethod
    def _issue(
        field: FieldDefinition, origin: str, code: str, message: str
    ) -> ResolvedField:
        """Возвращает ошибку одного поля без частичного значения."""
        return ResolvedField(
            field.id.uuid,
            None,
            origin,
            issues=(FieldIssue(field.id.uuid, code, message),),
        )
