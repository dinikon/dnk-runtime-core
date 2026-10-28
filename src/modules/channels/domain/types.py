"""Структурные типы документа настроек без зависимости от транспорта."""

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[
    str, JsonValue
]
type JsonObject = dict[str, JsonValue]
