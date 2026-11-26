from dataclasses import dataclass, field
from typing import ClassVar
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.domain.feed.field_node.data import FieldNodeData
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.field_node.value_validation import (
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
class MoneyNodeDataVO(FieldNodeData):
    """Хранит получение суммы и необязательную валютную метку результата."""

    kind: ClassVar[FieldValueType] = FieldValueType.MONEY
    value_definition: MoneyValueDefinitionVO
    currency: CurrencyVO | None = None
    constraints: MoneyConstraintsVO = field(default_factory=MoneyConstraintsVO)
    transforms: tuple[TransformDefinitionVO, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет собственные денежные настройки без локали и исполнения расчёта."""
        if (
            (self.currency is not None and not isinstance(self.currency, CurrencyVO))
            or not isinstance(self.value_definition, MoneyValueDefinitionVO)
            or not isinstance(self.constraints, MoneyConstraintsVO)
        ):
            raise InvalidFieldDefinitionError(
                "Нужны MoneyValueDefinitionVO, MoneyConstraintsVO и CurrencyVO либо None."
            )
        transforms = validate_transforms(
            self.transforms, allowed=frozenset((TransformOperation.MONEY_CEIL_STEP,))
        )
        object.__setattr__(self, "transforms", transforms)
