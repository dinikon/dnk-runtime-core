from datetime import datetime
from copy import deepcopy
from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from urllib.parse import urlsplit
from src.modules.channels.domain.external_publication.value_object.core import JsonValue
from src.modules.channels.domain.error import ChannelsValidationError


@dataclass(frozen=True, slots=True)
class ImportImageVO:
    """Сохраняет адрес и подпись изображения в неизменяемом снимке источника."""

    id: str
    url: str
    alt: str = ""

    def __post_init__(self) -> None:
        """Отклоняет неоднозначную identity и небезопасный адрес до переноса."""
        try:
            parsed = urlsplit(self.url)
            port = parsed.port
        except ValueError:
            raise ChannelsValidationError("invalid_import_image") from None
        if (
            not self.id
            or len(self.id) > 200
            or len(self.url) > 4096
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or port not in (None, 443)
            or len(self.alt) > 1000
        ):
            raise ChannelsValidationError("invalid_import_image")


@dataclass(frozen=True, slots=True)
class ImportSnapshotVO:
    """Описывает содержимое источника, а не редактируемую карточку Catalog."""

    translations: dict[str, dict[str, str | None]]
    images: tuple[ImportImageVO, ...]
    values: dict[str, JsonValue]
    warnings: tuple[str, ...]
    read_at: datetime | None = None
    source_updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Проверяет границы снимка и изолирует вложенные словари от вызывающего кода."""
        if (
            not 1 <= len(self.translations) <= 2
            or len(self.images) > 100
            or len({i.id for i in self.images}) != len(self.images)
        ):
            raise ChannelsValidationError("invalid_import_snapshot")
        for locale, content in self.translations.items():
            if not locale or len(locale) > 35 or set(content) != {"title", "body"}:
                raise ChannelsValidationError("invalid_import_translation")
            for key, limit in (("title", 2000), ("body", 300000)):
                value = content[key]
                if value is not None and (
                    not isinstance(value, str) or len(value) > limit
                ):
                    raise ChannelsValidationError("invalid_import_translation")
        if any(
            value is not None and value.utcoffset() is None
            for value in (self.read_at, self.source_updated_at)
        ):
            raise ChannelsValidationError("invalid_import_timestamp")
        object.__setattr__(self, "translations", deepcopy(self.translations))
        object.__setattr__(self, "values", deepcopy(self.values))


@dataclass(frozen=True, slots=True)
class PreparedImageVO:
    """Хранит результат одной попытки переноса фотографии."""

    file_id: EntityIdVO | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        """Различает ожидание, успех и ошибку, не допуская двух результатов сразу."""
        if self.file_id is not None and not isinstance(self.file_id, EntityIdVO):
            raise ChannelsValidationError("invalid_import_file_identifier")
        if self.file_id is not None and self.error_code is not None:
            raise ChannelsValidationError("invalid_prepared_image")
