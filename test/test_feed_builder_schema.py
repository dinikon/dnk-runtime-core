"""Рабочая схема Feed: Domain, сценарии и закрытые HTTP-контракты."""

import copy
from dataclasses import replace
from datetime import timedelta
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from pydantic import ValidationError
from test.test_feed_builder_domain import feed, NOW
from test.test_feed_builder_crud import rich_feed
from src.modules.feed_builder.application.feed.graph.codec import decode_schema
from src.modules.feed_builder.application.feed.graph.codec import schema_document
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.command import (
    SaveFeedSchemaDraftCommand,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.handler import (
    SaveFeedSchemaDraftHandler,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedDomainError,
    FeedArchivedError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.presentation.feed.http.request.put_feed_schema import (
    PutFeedSchemaRequest,
)
from src.modules.feed_builder.presentation.feed.http.schema.graph import (
    FieldGraphSchema,
)
from src.modules.feed_builder.presentation.feed.http.schema.body_limit import (
    excessive_json_depth,
)


def source_schema_document() -> dict:
    """Возвращает четыре равноправных поля с прямыми источниками и точными настройками."""
    result = schema_document(rich_feed().schema)
    for field, path in zip(
        result["fields"],
        ["item.title", "item.description", "item.sku", "item.regular_price"],
    ):
        t = field["data"]
        t["value"] = (
            {"kind": "MONEY", "mode": "SOURCE"}
            if field["typeId"] == "core.money"
            else {"kind": "SOURCE"}
        ) | {"source": {"provider": "catalog", "path": path}}
        if path in ("item.title", "item.description"):
            t["locale"] = "uk"
    result["fields"][-1]["data"]["constraints"]["min_amount"] = "1E-18"
    return result


def category_graph_field(
    key: str, name: str, data: dict, export: dict
) -> tuple[dict, dict]:
    """Создаёт связанную ноду Offer и дерево категорий графа V2."""
    identifier = str(uuid4())
    field = {
        "id": identifier,
        "key": key,
        "name": name,
        "typeId": "core.category_reference",
        "typeVersion": 1,
        "scope": "offer",
        "data": {"source": "feed", "treeId": identifier},
        "export": {"name": key, "enabled": True} | export,
    }
    return field, {"id": identifier, "data": data}


def category_schema_document(
    nodes: list[dict], extra_fields: tuple[dict, ...] = ()
) -> dict:
    """Возвращает схему с одним деревом и заданными записями."""
    field, tree = category_graph_field(
        "categoryId",
        "Категория",
        {
            "locale": "ru",
            "object_schema": {
                "id_key": "id",
                "label_key": "name",
                "fields": [
                    {
                        "key": "id",
                        "kind": "string",
                        "required": True,
                        "xml": {"placement": "ATTRIBUTE"},
                    },
                    {"key": "name", "kind": "text", "required": True},
                    *extra_fields,
                ],
            },
            "value": {
                "kind": "INLINE",
                "nodes": nodes,
                "rules": [],
                "fallback": "NONE",
            },
        },
        {"document": {"container": "categories", "item": "category"}},
    )
    return {"schema_format_version": 2, "fields": [field], "categoryTrees": [tree]}


class FeedSchemaDomainTests(TestCase):
    """Проверяет атомарную замену и неизменность исходного frozen-корня."""

    def test_change_noop_order_identity_and_empty(self) -> None:
        """Сохраняет ID, даты, настройки, порядок и версию реального изменения."""
        original = feed()
        schema = decode_schema(source_schema_document())
        saved = original.change_schema(schema=schema, now=NOW + timedelta(seconds=1))
        self.assertEqual(saved.version.value, 2)
        self.assertEqual(saved.id, original.id)
        self.assertEqual(saved.export_settings, original.export_settings)
        self.assertEqual(saved.created_at, original.created_at)
        self.assertEqual(original.schema.fields, ())
        self.assertIs(
            saved.change_schema(schema=schema, now=NOW + timedelta(seconds=2)), saved
        )
        reversed_schema = FeedSchemaVO(tuple(reversed(schema.fields)))
        reordered = saved.change_schema(
            schema=reversed_schema, now=NOW + timedelta(seconds=2)
        )
        self.assertEqual(
            [f.id for f in reordered.schema.fields],
            [f.id for f in reversed_schema.fields],
        )
        self.assertEqual(
            reordered.change_schema(
                schema=FeedSchemaVO(), now=NOW + timedelta(seconds=3)
            ).schema.fields,
            (),
        )

    def test_invalid_schema_and_archive_never_partially_change_root(self) -> None:
        """Отклоняет дубликаты, несовместимые источники, язык SKU и отсутствие локали."""
        original = feed()
        document = source_schema_document()
        invalid = []
        for key in ("id", "key"):
            value = copy.deepcopy(document)
            value["fields"][1][key] = value["fields"][0][key]
            invalid.append(value)
        value = copy.deepcopy(document)
        value["fields"][1]["export"]["name"] = value["fields"][0]["export"]["name"]
        invalid.append(value)
        value = copy.deepcopy(document)
        value["fields"][0]["data"]["value"]["source"]["path"] = "item.regular_price"
        invalid.append(value)
        value = copy.deepcopy(document)
        value["fields"][0]["data"]["locale"] = None
        invalid.append(value)
        value = copy.deepcopy(document)
        value["fields"][2]["data"]["locale"] = "uk"
        invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(FeedDomainError):
                original.change_schema(schema=decode_schema(value), now=NOW)
            self.assertEqual(original.schema.fields, ())
        with self.assertRaises(FeedArchivedError):
            original.archive(now=NOW).change_schema(
                schema=decode_schema(document), now=NOW
            )
        with self.assertRaises(FeedDomainError):
            original.change_schema(
                schema=decode_schema(document), now=NOW - timedelta(seconds=1)
            )

    def test_typed_http_ast_roundtrip_has_no_injected_null_properties(self) -> None:
        """Сохраняет все известные узлы, AI, Decimal-строки, transforms и nullable currency."""
        for source in (schema_document(rich_feed().schema), source_schema_document()):
            schema = FieldGraphSchema.model_validate(source)
            wire = schema.model_dump(mode="json", exclude_unset=True)
            self.assertEqual(wire, source)
            self.assertEqual(schema_document(decode_schema(wire)), source)

    def test_category_field_preserves_ids_and_rejects_cycles(self) -> None:
        """Сохраняет экспортные ID записей и проверяет целостность дерева V2."""
        first, second, third = map(str, (uuid4(), uuid4(), uuid4()))
        graph = category_schema_document(
            [
                {"id": first, "values": {"id": "1", "name": "Родитель"}},
                {
                    "id": second,
                    "parent_id": first,
                    "values": {"id": "2", "name": "Дочерняя"},
                },
            ]
        )
        previous = decode_schema(graph)
        document = schema_document(previous)
        self.assertEqual(schema_document(decode_schema(document)), document)
        value = document["categoryTrees"][0]["data"]["value"]
        value["nodes"] = [
            {"id": first, "values": {"name": "Переименована"}},
            {"id": third, "values": {"name": "Новая"}},
        ]
        changed = schema_document(decode_schema(document, previous_schema=previous))
        nodes = changed["categoryTrees"][0]["data"]["value"]["nodes"]
        self.assertEqual([node["values"]["id"] for node in nodes], ["1", "3"])
        value["nodes"][0]["values"]["id"] = "9"
        with self.assertRaises(InvalidFeedSchemaDocumentError):
            decode_schema(document, previous_schema=previous)
        value["nodes"][0]["values"].pop("id")
        value["nodes"][0]["parent_id"] = third
        value["nodes"][1]["parent_id"] = first
        with self.assertRaises(FeedDomainError):
            decode_schema(document)

    def test_v2_category_nodes_reference_one_feed_tree(self) -> None:
        """Хранит дерево отдельно, связывает его с нодой и сохраняет экспортный ID."""
        graph = category_schema_document(
            [
                {"id": str(uuid4()), "values": {"id": "100", "name": "Аудио"}},
            ]
        )
        saved = feed().change_schema(schema=decode_schema(graph), now=NOW)
        self.assertEqual(
            saved.schema.fields[0].category_tree_id, saved.schema.category_trees[0].id
        )
        wire = schema_document(saved.schema)
        self.assertEqual(wire["fields"][0]["data"], graph["fields"][0]["data"])
        self.assertEqual(
            wire["categoryTrees"][0]["data"]["value"]["nodes"][0]["values"]["id"], "100"
        )
        self.assertEqual(schema_document(decode_schema(wire)), wire)
        graph["categoryTrees"] = []
        with self.assertRaises(InvalidFeedSchemaDocumentError):
            decode_schema(graph)

    def test_category_properties_can_share_an_xml_name(self) -> None:
        """Сохраняет значения одноимённых атрибута и тега в дереве V2."""
        definition = category_schema_document(
            [
                {
                    "id": str(uuid4()),
                    "values": {
                        "id": "1",
                        "name": "Расходные материалы",
                        "code": "WH-01",
                        "element_code": 0,
                    },
                },
            ],
            (
                {
                    "key": "code",
                    "kind": "string",
                    "xml": {"placement": "ATTRIBUTE", "name": "code"},
                },
                {
                    "key": "element_code",
                    "kind": "integer",
                    "xml": {"placement": "ELEMENT", "name": "code"},
                },
            ),
        )
        canonical = schema_document(decode_schema(definition))
        FieldGraphSchema.model_validate(canonical)
        category = canonical["categoryTrees"][0]["data"]
        values = category["value"]["nodes"][0]["values"]
        codes = {
            prop["xml"]["placement"]: values[prop["key"]]
            for prop in category["object_schema"]["fields"]
            if prop["xml"]["name"] == "code"
        }
        self.assertEqual(codes, {"ATTRIBUTE": "WH-01", "ELEMENT": 0})

    def test_text_constant_obeys_character_and_length_constraints(self) -> None:
        """Отличает недопустимый текст константы от обычной ошибки источника."""
        definition = source_schema_document()
        settings = definition["fields"][0]["data"]
        settings.update(
            locale=None,
            fallback_policy=None,
            transforms=[],
            constraints={"required": True, "min_length": 1, "max_length": 3},
        )
        for value in ("    ", "r\n", "too long", "\x00"):
            with self.subTest(value=value):
                settings["value"] = {"kind": "CONSTANT", "value": value}
                with self.assertRaises(FeedDomainError) as error:
                    decode_schema(definition)
                self.assertEqual(error.exception.path[-3:], ("data", "value", "value"))
        settings["value"] = {"kind": "CONSTANT", "value": False}
        with self.assertRaises(FeedDomainError):
            decode_schema(definition)

    def test_xml_attribute_roundtrip_and_reserved_name(self) -> None:
        """Читает размещение по умолчанию и сохраняет выбор атрибута с проверкой имени."""
        definition = source_schema_document()
        self.assertIs(
            decode_schema(definition).fields[0].export.xml_placement,
            XmlFieldPlacement.ELEMENT,
        )
        export = definition["fields"][0]["export"]
        export.update(name="id", xml_placement="ATTRIBUTE")
        wire = FieldGraphSchema.model_validate(definition).model_dump(
            mode="json", exclude_unset=True
        )
        self.assertEqual(schema_document(decode_schema(wire)), definition)

        export["name"] = "xmlns"
        with self.assertRaises(FeedDomainError) as error:
            decode_schema(definition)
        self.assertEqual(
            error.exception.path, ("definition", "fields", 0, "export", "name")
        )
        export["xml_placement"] = True
        with self.assertRaises(ValidationError):
            FieldGraphSchema.model_validate(definition)

    def test_http_rejects_unknown_shapes_cross_type_settings_and_limits(self) -> None:
        """Отклоняет прямые обходы UI, старые aliases, неточные суммы и чужие свойства."""
        document = source_schema_document()
        for target, key, value in [
            ("data", "currency", "USD"),
            ("field", "locale", "uk"),
            ("source", "path", "item.arbitrary"),
            ("data", "value_type", "STRING"),
        ]:
            source = copy.deepcopy(document)
            field = source["fields"][0]
            item = (
                field
                if target == "field"
                else (
                    field["data"]["value"]["source"]
                    if target == "source"
                    else field["data"]
                )
            )
            item[key] = value
            with (
                self.subTest(key=key),
                self.assertRaises((InvalidFeedSchemaDocumentError, FeedDomainError)),
            ):
                decode_schema(source)
        value = copy.deepcopy(document)
        value["fields"][-1]["data"]["constraints"]["min_amount"] = 0.1
        with self.assertRaises(InvalidFeedSchemaDocumentError):
            decode_schema(value)
        for version in (None, 0, True, "1"):
            with self.assertRaises(ValidationError):
                PutFeedSchemaRequest.model_validate(
                    {"expected_version": version, "definition": document}
                )
        with self.assertRaises((InvalidFeedSchemaDocumentError, FeedDomainError)):
            decode_schema(
                {
                    "schema_format_version": 2,
                    "fields": [document["fields"][0]] * 201,
                }
            )
        self.assertTrue(excessive_json_depth(b"[" * 200 + b"0" + b"]" * 200))
        self.assertFalse(excessive_json_depth(b'{"text":"' + b"[" * 200 + b'"}'))

    def test_v1_is_rejected_by_http_and_storage_decoder(self) -> None:
        """Отклоняет старый граф на обеих границах без подстановки пустой схемы."""
        definition = {
            "schema_format_version": 1,
            "root": {"key": "publication", "kind": "object", "fields": []},
        }
        with self.assertRaises(ValidationError):
            PutFeedSchemaRequest.model_validate(
                {"expected_version": 1, "definition": definition}
            )
        with self.assertRaises(InvalidFeedSchemaDocumentError):
            decode_schema(definition)


class FeedSchemaApplicationTests(IsolatedAsyncioTestCase):
    """Проверяет явное сохранение пустого V2, версии и правила записи."""

    async def asyncSetUp(self) -> None:
        """Собирает сценарий без инфраструктуры."""
        self.original = rich_feed()
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.original), save=AsyncMock()
        )
        self.handler = SaveFeedSchemaDraftHandler(
            self.repository, Mock(now=lambda: NOW), AsyncMock(), Mock(side_effect=str)
        )

    async def test_save_clears_fields_once(self) -> None:
        """Очищает старые поля через корень и сохраняет версию при повторе."""
        command = SaveFeedSchemaDraftCommand(
            self.original.id, 1, schema_document(FeedSchemaVO())
        )
        result = await self.handler.execute(command)
        self.assertEqual(result.version, 2)
        self.assertEqual(result.definition["fields"], [])
        saved = self.repository.save.call_args.args[0]
        self.assertEqual(saved.schema.fields, ())
        self.assertEqual(saved.export_settings, self.original.export_settings)
        self.repository.get_for_update.return_value = saved
        self.repository.save.reset_mock()
        same = await self.handler.execute(replace(command, expected_version=2))
        self.assertEqual(same.version, 2)
        self.repository.save.assert_not_awaited()

    async def test_conflict_and_archive_do_not_write(self) -> None:
        """Ожидаемые отказы оставляют хранилище и исходный агрегат нетронутыми."""
        with self.assertRaises(FeedVersionConflictError):
            await self.handler.execute(
                SaveFeedSchemaDraftCommand(
                    self.original.id, 2, schema_document(FeedSchemaVO())
                )
            )
        self.repository.get_for_update.return_value = self.original.archive(now=NOW)
        with self.assertRaises(FeedArchivedError):
            await self.handler.execute(
                SaveFeedSchemaDraftCommand(
                    self.original.id, 2, schema_document(FeedSchemaVO())
                )
            )
        self.repository.save.assert_not_awaited()
