from src.modules.feed_builder.application.feed.command.update_feed.command import (
    UpdateFeedCommand,
)
from src.modules.feed_builder.application.feed.command.update_feed.dto import (
    UpdateFeedResultDTO,
)
from src.modules.feed_builder.application.feed.export_settings import (
    settings_from_dto,
    settings_to_dto,
)
from src.modules.feed_builder.application.feed.port.settings_repository import FeedSettingsRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.error import (
    FeedVersionConflictError,
    InvalidFeedValueError,
)


class UpdateFeedHandler:
    """Атомарно меняет настройки загруженного агрегата без изменения схемы."""

    def __init__(self, repository: FeedSettingsRepositoryProtocol, clock: ClockPort) -> None:
        """Принимает зависимости сценария без сессии или собственного UoW."""
        self._repository = repository
        self._clock = clock

    async def execute(self, command: UpdateFeedCommand) -> UpdateFeedResultDTO:
        """Проверяет версию, вызывает Domain и сохраняет только фактическое изменение."""
        expected = FeedVersionVO(command.expected_version)
        if (
            command.name is None
            and command.code is None
            and command.export_settings is None
        ):
            raise InvalidFeedValueError("Нужно передать хотя бы одно изменение.")
        locked = await self._repository.get_settings_for_update(command.feed_id)
        original = locked.feed
        if original.version != expected:
            raise FeedVersionConflictError("Feed уже изменён.")
        result = original.change_settings(
            name=(
                FeedNameVO(command.name) if command.name is not None else original.name
            ),
            code=(
                FeedCodeVO(command.code) if command.code is not None else original.code
            ),
            export_settings=(
                settings_from_dto(command.export_settings)
                if command.export_settings is not None
                else original.export_settings
            ),
            now=self._clock.now(),
        )
        if result is not original:
            await self._repository.save_settings(result, expected_version=expected)
        return UpdateFeedResultDTO(
            id=result.id.uuid,
            name=result.name.value,
            code=result.code.value,
            status=result.status.value,
            export_settings=settings_to_dto(result.export_settings),
            schema=locked.graph_document,
            version=result.version.value,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
