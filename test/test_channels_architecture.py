"""Исполняемые ограничения архитектуры Channels; запускаются без зависимостей БД."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src/modules/channels"
SCENARIOS = {
    "create_channel": ("command", "CreateChannelResultDTO", "CreateChannelResponse"),
    "update_channel": ("command", "UpdateChannelResultDTO", "UpdateChannelResponse"),
    "delete_channel": ("command", "None", None),
    "get_channel": ("query", "ChannelDetailsDTO", "GetChannelResponse"),
    "list_channels": (
        "query",
        "tuple[ChannelListItemDTO, ...]",
        "ListChannelItemResponse",
    ),
    "list_kinds": (
        "query",
        "tuple[ChannelKindListItemDTO, ...]",
        "ListChannelKindItemResponse",
    ),
    "get_kind_config": ("query", "ChannelKindConfigDTO", "GetKindConfigResponse"),
}


def parsed_files():
    for path in sorted(ROOT.rglob("*.py")):
        yield path.relative_to(ROOT), ast.parse(path.read_text(), filename=str(path))


class ChannelsArchitectureTests(unittest.TestCase):
    def test_use_cases_have_explicit_inputs_handlers_and_own_result_contracts(self):
        for scenario, (category, result, response) in SCENARIOS.items():
            with self.subTest(scenario=scenario):
                folder = ROOT / "application" / category / scenario
                self.assertTrue((folder / f"{category}.py").is_file())
                handler = ast.parse((folder / "handler.py").read_text())
                execute = next(
                    n
                    for n in ast.walk(handler)
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "execute"
                )
                self.assertEqual(ast.unparse(execute.returns), result)
                dto_path = folder / "dto.py"
                self.assertEqual(dto_path.is_file(), result != "None")
                if result != "None":
                    dto_name = result.removeprefix("tuple[").split(",")[0]
                    self.assertIn(
                        dto_name,
                        [
                            n.name
                            for n in ast.parse(dto_path.read_text()).body
                            if isinstance(n, ast.ClassDef)
                        ],
                    )
                    self.assertTrue(
                        any(
                            isinstance(n, ast.ImportFrom)
                            and n.module
                            == f"src.modules.channels.application.{category}.{scenario}.dto"
                            for n in handler.body
                        )
                    )
                self.assertTrue(
                    (ROOT / "presentation/http/controller" / f"{scenario}.py").is_file()
                )
                self.assertEqual(
                    (ROOT / "presentation/http/request" / f"{scenario}.py").is_file(),
                    scenario in {"create_channel", "update_channel"},
                )
                response_path = ROOT / "presentation/http/response" / f"{scenario}.py"
                self.assertEqual(response_path.is_file(), response is not None)
                if response:
                    definitions = [
                        n.name
                        for n in ast.parse(response_path.read_text()).body
                        if isinstance(n, ast.ClassDef)
                    ]
                    self.assertEqual(definitions, [response])
        self.assertFalse((ROOT / "presentation/http/response/channel.py").exists())

    def test_all_functions_have_complete_annotations_and_russian_documentation(self):
        for path, tree in parsed_files():
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    with self.subTest(path=path, function=node.name):
                        self.assertIsNotNone(node.returns)
                        args = [
                            *node.args.posonlyargs,
                            *node.args.args,
                            *node.args.kwonlyargs,
                        ]
                        args += [a for a in (node.args.vararg, node.args.kwarg) if a]
                        for arg in args:
                            if arg.arg not in {"self", "cls"}:
                                self.assertIsNotNone(arg.annotation, arg.arg)
                if isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    with self.subTest(path=path, definition=node.name):
                        self.assertRegex(ast.get_docstring(node) or "", "[А-Яа-яЁё]")

    def test_post_init_is_only_allowed_in_value_objects(self):
        for path, tree in parsed_files():
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "__post_init__"
                ):
                    self.assertEqual(
                        path.parts[:2], ("domain", "value_object"), str(path)
                    )
        tree = ast.parse((ROOT / "domain/aggregate.py").read_text())
        aggregate = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        methods = {n.name: n for n in aggregate.body if isinstance(n, ast.FunctionDef)}
        for name in ("create", "restore"):
            self.assertIn(
                "classmethod", [ast.unparse(d) for d in methods[name].decorator_list]
            )
        for name in ("rename", "set_active", "change_settings"):
            self.assertIn(name, methods)

    def test_dependencies_point_inward_and_transactions_stay_outside(self):
        external = ("sqlalchemy", "fastapi", "pydantic", "jsonschema", "cryptography")
        for path, tree in parsed_files():
            layer = path.parts[0]
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                    self.assertFalse(
                        any(alias.name == "*" for alias in node.names), str(path)
                    )
                elif isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                for module in modules:
                    with self.subTest(path=path, imported=module):
                        if layer in {"domain", "application"}:
                            self.assertFalse(module.startswith(external))
                            self.assertFalse(
                                module.startswith(
                                    (
                                        "src.config",
                                        "src.modules.channels.infrastructure",
                                        "src.modules.channels.presentation",
                                    )
                                )
                            )
                        if layer == "domain":
                            self.assertFalse(
                                module.startswith(
                                    ("src.modules.channels.application", "logging")
                                )
                            )
                        if layer == "presentation" and path.name != "depends.py":
                            self.assertFalse(
                                module.startswith("src.modules.channels.infrastructure")
                            )
                if (
                    layer in {"application", "infrastructure"}
                    and isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                ):
                    self.assertNotIn(node.func.attr, {"commit", "rollback"}, str(path))
                if layer == "application" and isinstance(node, ast.Attribute):
                    self.assertNotIn(
                        node.attr, {"session", "session_factory"}, str(path)
                    )
                if (
                    layer == "application"
                    and isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                ):
                    if node.func.attr == "execute":
                        self.fail(f"Application scenario calls another handler: {path}")

    def test_read_mapping_and_write_mapping_have_distinct_responsibilities(self):
        persistence = ROOT / "infrastructure/persistence"
        for name in (
            "mapper.py",
            "query_mapper.py",
            "repository.py",
            "query_repository.py",
            "models/channel.py",
        ):
            self.assertTrue((persistence / name).is_file())
        query = (persistence / "query_repository.py").read_text()
        self.assertNotIn("encrypted_secrets", query)
        self.assertNotIn("ChannelMapper", query)
        self.assertIn("ChannelQueryMapper.to_details", query)
        self.assertIn("ChannelQueryMapper.to_list_item", query)
        for filename in ("mapper.py", "query_mapper.py"):
            tree = ast.parse((persistence / filename).read_text())
            for node in ast.walk(tree):
                self.assertNotIsInstance(node, ast.Await)
        query_mapper = (persistence / "query_mapper.py").read_text()
        self.assertNotIn(".domain.aggregate", query_mapper)
        self.assertNotIn("decrypt", query_mapper)
        self.assertIn("Channel.restore(", (persistence / "mapper.py").read_text())
        self.assertIn(".with_for_update()", (persistence / "repository.py").read_text())

    def test_package_initializers_are_empty_and_single_root_is_not_nested(self):
        for path in ROOT.rglob("__init__.py"):
            self.assertEqual(ast.parse(path.read_text()).body, [], str(path))
        for layer in ("domain", "application", "infrastructure", "presentation"):
            self.assertFalse((ROOT / layer / "channel").exists())

    def test_controllers_map_their_own_dto_and_expected_errors(self):
        for scenario, (_, _, response) in SCENARIOS.items():
            source = (
                ROOT / "presentation/http/controller" / f"{scenario}.py"
            ).read_text()
            with self.subTest(scenario=scenario):
                self.assertIn("AuthenticatedRequestContextDep", source)
                self.assertIn("require_channel_context(context)", source)
                self.assertIn("except ChannelNotFoundError", source)
                if response:
                    self.assertIn(f"{response}.from_dto(", source)
                if scenario in {"create_channel", "update_channel"}:
                    for error in (
                        "ChannelValidationError",
                        "ChannelConfigConflictError",
                        "ChannelSecretsUnavailableError",
                        "InvalidChannelError",
                    ):
                        self.assertIn(f"except {error}", source)
                    self.assertNotIn("GetChannelHandler", source)
        router = (ROOT / "presentation/router.py").read_text()
        for scenario, (_, _, response) in SCENARIOS.items():
            if response:
                self.assertIn(f"http.response.{scenario} import", router)


if __name__ == "__main__":
    unittest.main()
