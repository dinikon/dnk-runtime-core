from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.calculation.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.calculation.evaluator import (
    MoneyFieldCalculator,
)
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
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
from src.modules.feed_builder.domain.feed.value_object.truncate_parameters import (
    TruncateParametersVO,
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
    value: str | PriceValueVO | None
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
        if isinstance(value, str) and not isinstance(settings, MoneyFieldTypeVO):
            if (
                any("\ud800" <= character <= "\udfff" for character in value)
                or "\x00" in value
                or (
                    isinstance(settings, StringFieldTypeVO)
                    and ("\n" in value or "\r" in value)
                )
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

        definition = settings.value_definition
        locale = None
        manual_translation = False
        if override is not None:
            value = override.value
            origin = "MANUAL"
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
            for transform in settings.transforms:
                if transform.operation is TransformOperation.STRING_TRIM:
                    value = value.strip()
                elif isinstance(transform.parameters, TruncateParametersVO):
                    value = value[: transform.parameters.max_length]
        constraints = settings.constraints
        if manual_translation or (
            constraints.required and (value is None or not value.strip())
        ):
            return self._issue(
                field, origin, "REQUIRED_VALUE_MISSING", "Требуется значение поля."
            )
        if value is not None and (
            (constraints.min_length is not None and len(value) < constraints.min_length)
            or (
                constraints.max_length is not None
                and len(value) > constraints.max_length
            )
        ):
            return self._issue(
                field, origin, "TEXT_LENGTH_CONSTRAINT", "Длина текста вне границ поля."
            )
        return ResolvedField(field.id.uuid, value, origin, locale)

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
