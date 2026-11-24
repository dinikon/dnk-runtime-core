"""Проверки собственных настроек типов без Policy агрегата и внешних метаданных."""

from __future__ import annotations
from typing import TYPE_CHECKING
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.limits import MAX_TRANSFORMS
from src.modules.feed_builder.domain.feed.validation import sequence
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constraints import (
    TextConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constant_value_definition import (
    TextConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.truncate_parameters import (
    TruncateParametersVO,
)

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import TextValueDefinition


def validate_transforms(
    transforms: tuple[TransformDefinitionVO, ...],
    *,
    allowed: frozenset[TransformOperation],
) -> tuple[TransformDefinitionVO, ...]:
    """Замораживает transforms и требует операций, допустимых данному типу."""
    result = sequence(transforms, label="Field type transforms", maximum=MAX_TRANSFORMS)
    if any(
        not isinstance(value, TransformDefinitionVO) or value.operation not in allowed
        for value in result
    ):
        raise InvalidFieldDefinitionError("Преобразование несовместимо с типом поля.")
    return result


def validate_text_settings(
    *,
    value_definition: TextValueDefinition,
    locale: LocaleCodeVO | None,
    fallback_policy: LocaleFallbackPolicyVO | None,
    constraints: TextConstraintsVO,
    transforms: tuple[TransformDefinitionVO, ...],
    multiline: bool,
) -> tuple[TransformDefinitionVO, ...]:
    """Проверяет общий состав двух текстовых типов без денежной ветви."""
    if not isinstance(
        value_definition,
        (
            SourceValueDefinitionVO,
            ManualValueDefinitionVO,
            TextConstantValueDefinitionVO,
        ),
    ) or not isinstance(constraints, TextConstraintsVO):
        raise InvalidFieldDefinitionError(
            "Текстовый тип требует текстовое определение и TextConstraintsVO."
        )
    if locale is not None and not isinstance(locale, LocaleCodeVO):
        raise InvalidFieldDefinitionError("Нужна типизированная локаль текста.")
    if fallback_policy is not None:
        if not isinstance(fallback_policy, LocaleFallbackPolicyVO):
            raise InvalidFieldDefinitionError("Нужна типизированная политика fallback.")
        if locale is None or locale in fallback_policy.locales:
            raise InvalidFieldDefinitionError(
                "Fallback требует целевую локаль и не повторяет её."
            )
    result = validate_transforms(
        transforms,
        allowed=frozenset(
            (TransformOperation.STRING_TRIM, TransformOperation.STRING_TRUNCATE)
        ),
    )
    if isinstance(value_definition, TextConstantValueDefinitionVO):
        path = ("type_definition", "value", "value")
        if locale is not None or fallback_policy is not None:
            raise InvalidFieldDefinitionError(
                "Заданное текстовое значение не использует локаль и резервные переводы.",
                path=("type_definition", "locale"),
            )
        if not valid_text_characters(value_definition.value, multiline=multiline):
            raise InvalidFieldDefinitionError(
                "Недопустимые символы для этого текстового поля.", path=path
            )
        value = apply_text_transforms(value_definition.value, result)
        if constraints.required and not value.strip():
            raise InvalidFieldDefinitionError("Требуется значение поля.", path=path)
        if not constraints.accepts_length(value):
            raise InvalidFieldDefinitionError(
                "Длина текста вне границ поля.", path=path
            )
    return result


def valid_text_characters(value: str, *, multiline: bool) -> bool:
    """Проверяет сохраняемый текст и переносы в однострочном поле."""
    return (
        "\x00" not in value
        and not any("\ud800" <= character <= "\udfff" for character in value)
        and (multiline or ("\n" not in value and "\r" not in value))
    )


def apply_text_transforms(
    value: str, transforms: tuple[TransformDefinitionVO, ...]
) -> str:
    """Применяет упорядоченные преобразования короткого и длинного текста."""
    for transform in transforms:
        if transform.operation is TransformOperation.STRING_TRIM:
            value = value.strip()
        elif isinstance(transform.parameters, TruncateParametersVO):
            value = value[: transform.parameters.max_length]
    return value
