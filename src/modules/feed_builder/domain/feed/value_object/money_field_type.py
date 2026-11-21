from dataclasses import dataclass, field
from typing import ClassVar
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.field_type_validation import (
    validate_transforms,
)
from src.modules.feed_builder.domain.feed.value_object.money_constraints import (
    MoneyConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_value_definition import (
    MoneyValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)


@dataclass(frozen=True, slots=True)
class MoneyFieldTypeVO:
    """Хранит обязательную валюту и настройки получения/проверки денежного значения."""

    kind: ClassVar[FieldValueType] = FieldValueType.MONEY
    currency: CurrencyVO
    value_definition: MoneyValueDefinitionVO
    constraints: MoneyConstraintsVO = field(default_factory=MoneyConstraintsVO)
    transforms: tuple[TransformDefinitionVO, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет собственные денежные настройки без локали и исполнения расчёта."""
        if (
            not isinstance(self.currency, CurrencyVO)
            or not isinstance(self.value_definition, MoneyValueDefinitionVO)
            or not isinstance(self.constraints, MoneyConstraintsVO)
        ):
            raise InvalidFieldDefinitionError(
                "Денежный тип требует CurrencyVO, MoneyValueDefinitionVO и MoneyConstraintsVO."
            )
        transforms = validate_transforms(
            self.transforms, allowed=frozenset((TransformOperation.MONEY_CEIL_STEP,))
        )
        object.__setattr__(self, "transforms", transforms)
