from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.command import (
    SaveFeedSchemaDraftCommand,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.dto import (
    SaveFeedSchemaDraftResultDTO,
)
from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocalesPort,
)
from src.modules.feed_builder.application.feed.schema_definition import decode_schema
from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.value_object.string_field_type import (
    StringFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_field_type import (
    TextFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedVersionConflictError,
    FeedArchivedError,
    InvalidFieldDefinitionError,
)
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.policy.calculation_semantics import (
    PriceCalculationSemanticPolicy,
)
from src.modules.feed_builder.domain.feed.calculation.error import (
    CalculationDefinitionError,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class SaveFeedSchemaDraftHandler:
    """Сохраняет рабочее определение через Feed в общей транзакции внешнего UoW."""

    def __init__(
        self,
        repository: FeedRepositoryProtocol,
        locales: SchemaLocalesPort,
        clock: ClockPort,
    ) -> None:
        """Принимает порты без HTTP, ORM или управления сессией."""
        self._repository = repository
        self._locales = locales
        self._clock = clock

    async def execute(
        self, command: SaveFeedSchemaDraftCommand
    ) -> SaveFeedSchemaDraftResultDTO:
        """Проверяет версию, метаданные и Domain, записывая только фактическое изменение."""
        expected = FeedVersionVO(command.expected_version)
        original = await self._repository.get_for_update(command.feed_id)
        if original.version != expected:
            raise FeedVersionConflictError("Feed уже изменён.")
        if original.status is FeedStatus.ARCHIVED:
            raise FeedArchivedError("Архивный Feed нельзя редактировать.")
        schema = decode_schema(command.definition, previous_schema=original.schema)
        previous_fields = {field.id: field for field in original.schema.fields}
        for index, field in enumerate(schema.fields):
            settings = field.type_definition
            if (
                not isinstance(settings, MoneyFieldTypeVO)
                or settings.value_definition.calculation is None
            ):
                continue
            previous = previous_fields.get(field.id)
            previous_settings = (
                previous.type_definition if previous is not None else None
            )
            if (
                isinstance(previous_settings, MoneyFieldTypeVO)
                and previous_settings.value_definition.calculation
                == settings.value_definition.calculation
            ):
                continue
            try:
                PriceCalculationSemanticPolicy.ensure_valid(
                    settings.value_definition.calculation
                )
            except CalculationDefinitionError as exc:
                exc.path = (
                    "definition",
                    "root",
                    "fields",
                    index,
                    "type_definition",
                    "value",
                    "calculation",
                    *exc.path,
                )
                raise
        result = original.change_schema(schema=schema, now=self._clock.now())
        needed: list[tuple[int, str]] = []
        for index, field in enumerate(schema.fields):
            settings = field.type_definition
            if isinstance(settings, CategoryFieldTypeVO) and any(
                node.catalog_id is not None for node in settings.nodes
            ):
                needed.append((index, settings.locale.value))
            if isinstance(settings, (StringFieldTypeVO, TextFieldTypeVO)):
                if settings.locale is not None:
                    needed.append((index, settings.locale.value))
                if settings.fallback_policy is not None:
                    needed.extend(
                        (index, item.value) for item in settings.fallback_policy.locales
                    )
        if needed:
            supported = {item.code for item in await self._locales.list_available()}
            for index, code in needed:
                if code not in supported:
                    raise InvalidFieldDefinitionError(
                        "Локаль недоступна в справочнике.",
                        path=(
                            "definition",
                            "root",
                            "fields",
                            index,
                            "type_definition",
                            "locale",
                        ),
                    )
        if result is not original:
            await self._repository.save(result, expected_version=expected)
        return SaveFeedSchemaDraftResultDTO(
            result.id.uuid, result.version.value, schema_document(result.schema)
        )
