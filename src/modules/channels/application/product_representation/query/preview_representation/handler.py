from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.product_representation.query.preview_representation.dto import (
    PreviewRepresentationResultDTO,
)
from src.modules.channels.application.product_representation.query.preview_representation.query import (
    PreviewRepresentationQuery,
)
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationReader,
)
from src.modules.channels.application.product_representation.service.drafts import (
    RepresentationDrafts,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class PreviewRepresentationHandler:
    """Проверяет сохранённое намерение или полный несохранённый черновик."""

    def __init__(
        self,
        *,
        reader: RepresentationReader,
        drafts: RepresentationDrafts,
        clock: ClockPort,
    ) -> None:
        """Получает read-координацию и общий путь подготовки без write-портов."""
        self._reader = reader
        self._drafts = drafts
        self._clock = clock

    async def execute(
        self, query: PreviewRepresentationQuery
    ) -> PreviewRepresentationResultDTO:
        """Читает актуальный снимок; preview никогда не меняет разрешение экспорта."""
        context = await self._reader.load(
            channel_id=query.channel_id, group_id=query.group_id
        )
        locales = query.locales if query.locales is not None else context.locales
        if (
            not locales
            or len(set(locales)) != len(locales)
            or any(locale not in context.locales for locale in locales)
        ):
            raise ChannelInputError("representation_locales_invalid", field="locales")
        if query.overrides is not None:
            if (
                query.expected_revision is None
                or query.expected_binding_revision is None
                or query.expected_config_revision is None
            ):
                raise ChannelInputError("representation_context_required")
            self._reader.require_context(
                context,
                expected_revision=query.expected_revision,
                expected_binding_revision=query.expected_binding_revision,
                expected_config_revision=query.expected_config_revision,
            )
        draft = await self._drafts.prepare(
            context=context,
            overrides=(
                query.overrides
                if query.overrides is not None
                else context.state.overrides
            ),
            locales=locales,
            as_of=self._clock.now(),
        )
        return PreviewRepresentationResultDTO(
            representation=draft.prepared,
            state=context.state,
            export_blockers=draft.export_blockers,
            draft=query.overrides is not None,
        )
