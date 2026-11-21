from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class SourceReferenceVO:
    """Хранит типизированную ссылку на разрешённый прямой источник без его чтения."""

    provider: SourceProvider
    path: CatalogSourcePath

    def __post_init__(self) -> None:
        """Требует Enum нужного типа и соответствие пути провайдеру без приведения строк."""
        if not isinstance(self.provider, SourceProvider):
            raise InvalidFeedValueError("Источник требует SourceProvider.")
        if self.provider is not SourceProvider.CATALOG or not isinstance(
            self.path, CatalogSourcePath
        ):
            raise InvalidFeedValueError(
                "Для провайдера Catalog нужен путь CatalogSourcePath."
            )
