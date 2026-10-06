from urllib.parse import urlsplit
from jsonschema import Draft202012Validator, FormatChecker
from src.modules.channels.domain.error import ChannelValidationError

formats = FormatChecker()


@formats.checks("https-store-url")
def valid_store_url(value):
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

    def validate(self, definition, settings):
        schema = definition.config["connection"]["json_schema"]
        validator = Draft202012Validator(schema, format_checker=formats)
        errors = []
        for error in validator.iter_errors(settings):
            path = ["body", "connection_settings", *error.absolute_path]
            if error.validator == "required":
                for key in error.validator_value:
                    if key not in error.instance:
                        errors.append(
                            {
                                "loc": path + [key],
                                "msg": "Обязательное поле.",
                                "type": "required",
                            }
                        )
            else:
                errors.append(
                    {
                        "loc": path,
                        "msg": "Некорректное значение поля.",
                        "type": str(error.validator),
                    }
                )
        if errors:
            raise ChannelValidationError(tuple(errors))
