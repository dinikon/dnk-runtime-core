from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.value_object.truncate_parameters import (
    TruncateParametersVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_ceil_step_parameters import (
    MoneyCeilStepParametersVO,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class TransformDefinitionVO:
    """Связывает преобразование с единственным допустимым типом параметров."""

    operation: TransformOperation
    parameters: TruncateParametersVO | MoneyCeilStepParametersVO | None = None

    def __post_init__(self) -> None:
        """Отклоняет неизвестную операцию и несовместимые параметры."""
        if not isinstance(self.operation, TransformOperation):
            raise InvalidFeedValueError("Нужна типизированная операция transform.")
        expected = {
            TransformOperation.STRING_TRIM: type(None),
            TransformOperation.STRING_TRUNCATE: TruncateParametersVO,
            TransformOperation.MONEY_CEIL_STEP: MoneyCeilStepParametersVO,
        }[self.operation]
        if not isinstance(self.parameters, expected):
            raise InvalidFeedValueError("Параметры не соответствуют transform.")
