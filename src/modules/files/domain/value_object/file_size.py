from dataclasses import dataclass
from src.modules.files.domain.error import InvalidFileError


@dataclass(frozen=True, slots=True)
class FileSizeVO:
    """Неотрицательный размер файла в байтах."""

    value: int

    def __post_init__(self) -> None:
        """Проверяет размер, включая допустимый пустой файл."""
        if (
            not isinstance(self.value, int)
            or isinstance(self.value, bool)
            or self.value < 0
        ):
            raise InvalidFileError("Invalid file size.")
