class InvalidFileQueryError(Exception):
    """Параметры чтения файлового менеджера не соответствуют контракту сценария."""


class UnsupportedFilePreviewError(Exception):
    """Формат файла не входит в явно поддержанные форматы предпросмотра."""
