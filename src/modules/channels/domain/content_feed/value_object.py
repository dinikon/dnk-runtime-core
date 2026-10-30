from copy import deepcopy
from dataclasses import dataclass, field

from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.types import JsonObject


@dataclass(frozen=True, slots=True)
class FeedSourceVO:
    """Неизменяемый снимок проверенных пакетом параметров исходного документа."""

    schema: str
    _settings: JsonObject = field(repr=False)

    def __post_init__(self) -> None:
        """Защищает снимок от изменения входного словаря."""
        if not self.schema or not isinstance(self._settings, dict):
            raise ContentFeedError("feed_source_invalid")
        object.__setattr__(self, "_settings", deepcopy(self._settings))

    @property
    def settings(self) -> JsonObject:
        """Возвращает независимую копию параметров."""
        return deepcopy(self._settings)
