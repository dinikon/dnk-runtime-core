class InvalidFeedSchemaDocumentError(Exception):
    """Сообщает о некорректном транспортно-независимом документе схемы."""

    def __init__(self, message: str, *, path: tuple[str | int, ...] = ()) -> None:
        """Сохраняет безопасное сообщение и путь к недопустимому определению."""
        super().__init__(message)
        self.path = path
