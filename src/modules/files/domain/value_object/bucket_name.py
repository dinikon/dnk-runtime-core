from dataclasses import dataclass
import re
from src.modules.files.domain.error import InvalidStorageStateError


@dataclass(frozen=True, slots=True)
class BucketNameVO:
    """Физическое имя контейнера в выделенном namespace модуля."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет формат системного имени контейнера."""
        if not re.fullmatch(r"dnk-tenant-[0-9a-f]{32}", self.value):
            raise InvalidStorageStateError("Invalid system bucket name.")
