from collections.abc import Callable

from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.command import (
    SaveFeedSchemaDraftCommand,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.dto import (
    SaveFeedSchemaDraftResultDTO,
)
from src.modules.feed_builder.application.feed.graph.codec import (
    build_schema,
    schema_document,
)
from src.modules.feed_builder.application.feed.graph.validation import (
    validate_saved_graph,
)
from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocalesPort,
)
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.shared.domain.time.clock_port import ClockPort


class SaveFeedSchemaDraftHandler:
    """Сохраняет граф через агрегат Feed в общем внешнем UoW."""

    def __init__(
        self,
        repository: FeedRepositoryProtocol,
        clock: ClockPort,
        locales: SchemaLocalesPort,
        clean_html: Callable[[str], str],
    ) -> None:
        """Принимает порт хранения, справочник локалей и часы."""
        self._repository = repository
        self._clock = clock
        self._locales = locales
        self._clean_html = clean_html

    async def execute(
        self, command: SaveFeedSchemaDraftCommand
    ) -> SaveFeedSchemaDraftResultDTO:
        """Проверяет версию и записывает только фактическое изменение схемы."""
        expected = FeedVersionVO(command.expected_version)
        original = await self._repository.get_for_update(command.feed_id)
        if original.version != expected:
            raise FeedVersionConflictError("Feed уже изменён.")
        if original.status is FeedStatus.ARCHIVED:
            raise FeedArchivedError("Архивный Feed нельзя редактировать.")
        schema = build_schema(
            command.definition,
            previous_schema=original.schema,
            clean_html=self._clean_html,
        )
        result = original.change_schema(schema=schema, now=self._clock.now())
        await validate_saved_graph(schema, original.schema, self._locales)
        if result is not original:
            await self._repository.save(result, expected_version=expected)
        return SaveFeedSchemaDraftResultDTO(
            result.id.uuid, result.version.value, schema_document(result.schema)
        )
