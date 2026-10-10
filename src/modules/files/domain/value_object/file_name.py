from dataclasses import dataclass
from src.modules.files.domain.error import InvalidFileError


@dataclass(frozen=True, slots=True)
class FileNameVO:
    """Исходное имя файла, которое не используется как ключ хранения."""

    value: str

    def __post_init__(self) -> None:
        """Отклоняет пустые имена, пути и управляющие символы."""
        if (
            not self.value.strip()
            or len(self.value) > 255
            or any(ord(c) < 32 or ord(c) == 127 or c in "/\\" for c in self.value)
        ):
            raise InvalidFileError("Invalid file name.")
