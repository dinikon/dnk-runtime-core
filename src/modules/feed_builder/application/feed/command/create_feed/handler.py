from src.modules.feed_builder.application.feed.command.create_feed.command import (
    CreateFeedCommand,
)
from src.modules.feed_builder.application.feed.command.create_feed.dto import (
    CreateFeedResultDTO,
)
from src.modules.feed_builder.application.feed.export_settings import (
    settings_from_dto,
    settings_to_dto,
)
from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateFeedHandler:
    """Создаёт пустой DRAFT с явными настройками экспорта."""

    def __init__(
        self,
        repository: FeedRepositoryProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает зависимости сценария без сессии или собственного UoW."""
        self._repository = repository
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def execute(self, command: CreateFeedCommand) -> CreateFeedResultDTO:
        """Создаёт и сохраняет Feed; commit выполняется снаружи."""
        result = Feed.create(
            identifier=FeedIdVO.from_value(self._uuid_generator.new()),
            name=FeedNameVO(command.name),
            code=FeedCodeVO(command.code),
            export_settings=settings_from_dto(command.export_settings),
            now=self._clock.now(),
        )
        await self._repository.add(result)
        return CreateFeedResultDTO(
            id=result.id.uuid,
            name=result.name.value,
            code=result.code.value,
            status=result.status.value,
            export_settings=settings_to_dto(result.export_settings),
            schema=schema_document(result.schema),
            version=result.version.value,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
