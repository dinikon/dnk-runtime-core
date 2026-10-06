from urllib.parse import urlsplit
from jsonschema import Draft202012Validator, FormatChecker
from src.modules.channels.application.error import (
    ChannelFieldError,
    ChannelValidationError,
)
from src.modules.channels.application.port.registry import ChannelDefinition

formats = FormatChecker()


@formats.checks("https-store-url")
def valid_store_url(value: object) -> bool:
    """Проверяет абсолютный HTTPS URL магазина без credentials, query и fragment."""
    if not isinstance(value, str):
        return True
    try:
        parsed = urlsplit(value)
        port = parsed.port
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and "?" not in value
            and "#" not in value
            and "@" not in parsed.netloc
            and not any(c.isspace() or ord(c) < 32 for c in value)
            and "\\" not in value
            and (port is None or 1 <= port <= 65535)
        )
    except ValueError:
        return False


class JsonSchemaConnectionValidator:
    """Проверяет по опубликованной схеме; сообщения не содержат входные значения."""

    def validate(self, definition: ChannelDefinition, settings: dict[str, str]) -> None:
        """Проверяет формат и ограничения, не включая исходные значения в ошибки."""
        schema = definition.config["connection"]["json_schema"]
        validator = Draft202012Validator(schema, format_checker=formats)
        errors: list[ChannelFieldError] = []
        for error in validator.iter_errors(settings):
            path = ("connection_settings", *error.absolute_path)
            if error.validator == "required":
                for key in error.validator_value:
                    if key not in error.instance:
                        issue = ChannelFieldError(
                            path + (key,), "Обязательное поле.", "required"
                        )
                        if issue not in errors:
                            errors.append(issue)
            else:
                errors.append(
                    ChannelFieldError(
                        path,
                        "Некорректное значение поля.",
                        str(error.validator),
                    )
                )
        if errors:
            raise ChannelValidationError(tuple(errors))
