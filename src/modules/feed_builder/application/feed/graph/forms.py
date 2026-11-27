from dataclasses import dataclass
from typing import Literal

from src.modules.feed_builder.application.feed.graph.registry import NodeCodec
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType

type ControlKind = Literal[
    "input",
    "textarea",
    "rich_text",
    "select",
    "number",
    "decimal",
    "checkbox",
    "conditions",
    "categories",
    "transforms",
]


@dataclass(frozen=True, slots=True)
class FormControl:
    """Описывает контрол и путь к редактируемому параметру ноды."""

    kind: ControlKind
    path: str
    label: str
    options: tuple[str, ...] = ()
    options_source: str | None = None
    visible_in_modes: tuple[str, ...] = ()
    max_length: int | None = None

    def document(self) -> JsonObject:
        """Представляет дескриптор контрола для Console."""
        result: JsonObject = {"kind": self.kind, "path": self.path, "label": self.label}
        if self.options:
            result["options"] = list(self.options)
        if self.options_source is not None:
            result["optionsSource"] = self.options_source
        if self.visible_in_modes:
            result["visibleInModes"] = list(self.visible_in_modes)
        if self.max_length is not None:
            result["maxLength"] = self.max_length
        return result


_COMMON = (
    FormControl("input", "name", "Название", max_length=255),
    FormControl("input", "key", "Ключ", max_length=64),
    FormControl("input", "export.name", "Имя при выгрузке", max_length=128),
    FormControl("checkbox", "export.enabled", "Включить в выгрузку"),
    FormControl(
        "select", "export.xml_placement", "Размещение в XML", ("ELEMENT", "ATTRIBUTE")
    ),
    FormControl("textarea", "aiInstruction", "Инструкция для AI", max_length=10000),
)
_LOCALE = FormControl("select", "data.locale", "Локаль", options_source="locales")
_REQUIRED = FormControl("checkbox", "data.constraints.required", "Обязательное поле")
_TRANSFORMS = FormControl("transforms", "data.transforms", "Преобразования")
RICH_TEXT_OVERRIDE_CONTROL = FormControl(
    "rich_text", "value", "Форматированное описание"
)


def node_forms(codec: NodeCodec) -> JsonObject:
    """Собирает форму конструктора и ручного значения зарегистрированной ноды."""
    kind = codec.kind
    if kind is FieldValueType.CATEGORY:
        return {
            "settings": [
                item.document()
                for item in (*_COMMON, FormControl("categories", "data", "Категории"))
            ],
            "publicationOverride": [],
        }

    mode_path = "data.value.mode" if kind is FieldValueType.MONEY else "data.value.kind"
    controls = [
        FormControl("select", mode_path, "Получение значения", codec.modes),
        FormControl(
            "select",
            "data.value.source.path",
            "Источник Catalog",
            options_source="sources",
            visible_in_modes=("SOURCE",),
        ),
        _REQUIRED,
    ]
    if kind in (FieldValueType.STRING, FieldValueType.TEXT, FieldValueType.RICH_TEXT):
        text_editors: dict[FieldValueType, ControlKind] = {
            FieldValueType.STRING: "input",
            FieldValueType.TEXT: "textarea",
            FieldValueType.RICH_TEXT: "rich_text",
        }
        editor = text_editors[kind]
        controls.extend(
            (
                FormControl(
                    editor,
                    "data.value.value",
                    "Значение",
                    visible_in_modes=("CONSTANT",),
                ),
                _LOCALE,
                FormControl(
                    "number", "data.constraints.min_length", "Минимальная длина"
                ),
                FormControl(
                    "number", "data.constraints.max_length", "Максимальная длина"
                ),
                _TRANSFORMS,
            )
        )
    elif kind is FieldValueType.MONEY:
        editor = "decimal"
        controls.extend(
            (
                FormControl("input", "data.currency", "Валюта"),
                FormControl(
                    "decimal", "data.constraints.min_amount", "Минимальная сумма"
                ),
                FormControl(
                    "decimal", "data.constraints.max_amount", "Максимальная сумма"
                ),
                FormControl(
                    "conditions",
                    "data.value.calculation",
                    "Расчёт",
                    visible_in_modes=("CALCULATED",),
                ),
                _TRANSFORMS,
            )
        )
    elif kind is FieldValueType.INTEGER:
        editor = "number"
        controls.extend(
            (
                FormControl(
                    editor,
                    "data.value.value",
                    "Значение",
                    visible_in_modes=("CONSTANT",),
                ),
                FormControl("number", "data.constraints.min_value", "Минимум"),
                FormControl("number", "data.constraints.max_value", "Максимум"),
            )
        )
    else:
        editor = "checkbox"
        controls.extend(
            (
                FormControl(
                    editor,
                    "data.value.value",
                    "Значение",
                    visible_in_modes=("CONSTANT",),
                ),
                FormControl(
                    "conditions",
                    "data.value",
                    "Условия",
                    visible_in_modes=("CALCULATED",),
                ),
            )
        )
    common = _COMMON
    override = FormControl(editor, "value", codec.label)
    if kind is FieldValueType.RICH_TEXT:
        common = tuple(item for item in common if item.path != "export.xml_placement")
        override = RICH_TEXT_OVERRIDE_CONTROL
    return {
        "settings": [item.document() for item in (*common, *controls)],
        "publicationOverride": [override.document()],
    }
