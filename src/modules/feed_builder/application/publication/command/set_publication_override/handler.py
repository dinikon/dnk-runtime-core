from decimal import Decimal
import re

from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationOverrideError,
)
from src.modules.feed_builder.domain.publication.service.field_value_resolver import (
    FieldValueResolver,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.application.publication.command.set_publication_override.command import (
    SetPublicationOverrideCommand,
)
from src.modules.feed_builder.application.publication.command.set_publication_override.dto import (
    SetPublicationOverrideResultDTO,
)
from src.modules.feed_builder.application.publication.override_target import (
    load_override_target,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class SetPublicationOverrideHandler:
    """Выполняет изменение override в общей транзакции публикации."""

    def __init__(
        self,
        feeds: FeedRepositoryProtocol,
        publications: FeedPublicationRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Получает порты общей транзакции."""
        self._feeds, self._publications, self._clock = feeds, publications, clock

    async def execute(
        self, command: SetPublicationOverrideCommand
    ) -> SetPublicationOverrideResultDTO:
        """Проверяет текущую схему и обновляет одно поле."""
        original, field = await load_override_target(
            self._feeds,
            self._publications,
            feed_id=command.feed_id,
            publication_id=command.publication_id,
            field_id=command.field_id,
            expected_feed_version=command.expected_feed_version,
            expected_version=command.expected_version,
        )
        value: str | PriceAmountVO = command.value
        if isinstance(field.type_definition, MoneyFieldTypeVO):
            amount = command.value.strip()
            if re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)", amount) is None:
                raise InvalidPublicationOverrideError(
                    "INVALID_AMOUNT", "Введите десятичную сумму, например 1250.50."
                )
            try:
                value = PriceAmountVO(Decimal(amount))
            except InvalidFeedValueError as exc:
                raise InvalidPublicationOverrideError(
                    "INVALID_AMOUNT", str(exc)
                ) from exc
        override = FieldOverrideVO(field.id, value)
        reference = original.product_reference
        resolved = FieldValueResolver().resolve_manual(
            field, override, reference.catalog_variant_id or reference.catalog_item_id
        )
        if resolved.issues:
            issue = resolved.issues[0]
            raise InvalidPublicationOverrideError(issue.code, issue.message)
        result = original.set_override(override, now=self._clock.now())
        if result is not original:
            await self._publications.save(result, original.version)
        return SetPublicationOverrideResultDTO(result.version.value)
