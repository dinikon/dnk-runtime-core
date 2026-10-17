import logging


class RedactAccessQuery(logging.Filter):
    """Do not retain authorization codes or invitation tokens in access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            if isinstance(args[2], str):
                args[2] = args[2].split("?", 1)[0]
                record.args = tuple(args)
        return True


def install_access_log_redaction() -> None:
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, RedactAccessQuery) for item in logger.filters):
        logger.addFilter(RedactAccessQuery())
