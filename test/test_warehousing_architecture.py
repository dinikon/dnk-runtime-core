"""Нормативные границы и обязательные файлы первого среза Warehousing."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/modules/warehousing"
TIME_ZONE = (
    ROOT / "src/modules/reference_data/application/time_zone/query/check_time_zone"
)


class WarehousingArchitectureTests(unittest.TestCase):
    """Проверяет архитектуру отдельно от успешных функциональных тестов."""

    def test_dependencies_point_inward_and_imports_are_direct(self) -> None:
        """Внутренние слои не импортируют фреймворки и чужие модели."""
        forbidden = {
            "domain": (
                "sqlalchemy",
                "fastapi",
                "pydantic",
                "logging",
                "src.config",
                "src.modules.warehousing.application",
                "src.modules.warehousing.infrastructure",
                "src.modules.warehousing.presentation",
                "src.modules.shared.application",
                "src.modules.shared.infrastructure",
                "src.modules.shared.presentation",
            ),
            "application": (
                "sqlalchemy",
                "fastapi",
                "pydantic",
                "src.config",
                "src.modules.warehousing.infrastructure",
                "src.modules.warehousing.presentation",
                "src.modules.shared.infrastructure",
                "src.modules.shared.presentation",
            ),
            "infrastructure": ("src.modules.warehousing.presentation",),
        }
        for path in MODULE.rglob("*.py"):
            tree = ast.parse(path.read_text())
            layer = path.relative_to(MODULE).parts[0]
            if path.name == "__init__.py":
                self.assertEqual(path.read_text().strip(), "", str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    self.assertFalse(
                        name.startswith(forbidden.get(layer, ())), f"{path}: {name}"
                    )
                    if name.startswith("src.modules."):
                        self.assertTrue(
                            (ROOT / (name.replace(".", "/") + ".py")).is_file(),
                            f"Indirect import: {path}: {name}",
                        )
                        parts = name.split(".")
                        if parts[2] not in ("warehousing", "shared"):
                            if (
                                name
                                == "src.modules.tenancy.infrastructure.tenant.persistence.tenant_base"
                            ):
                                self.assertEqual(layer, "infrastructure")
                                continue
                            self.assertFalse(
                                parts[3] == "domain", f"Foreign Domain: {path}: {name}"
                            )
                            if layer in ("domain", "application", "infrastructure"):
                                self.assertFalse(
                                    parts[3] in ("infrastructure", "presentation"),
                                    f"Foreign adapter: {path}: {name}",
                                )

    def test_annotations_docstrings_and_post_init(self) -> None:
        """Новые методы аннотированы, документированы; post_init разрешён только VO."""
        paths = (
            list(MODULE.rglob("*.py"))
            + list(TIME_ZONE.glob("*.py"))
            + [ROOT / "migrations/tenant/versions/0017_warehousing_warehouses.py"]
        )
        for path in paths:
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    self.assertTrue(
                        ast.get_docstring(node),
                        f"Missing docstring: {path}: {node.name}",
                    )
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertIsNotNone(
                        node.returns, f"Missing return annotation: {path}: {node.name}"
                    )
                    args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                    args += [
                        arg
                        for arg in (node.args.vararg, node.args.kwarg)
                        if arg is not None
                    ]
                    for arg in args:
                        if arg.arg not in ("self", "cls"):
                            self.assertIsNotNone(
                                arg.annotation, f"{path}: {node.name}: {arg.arg}"
                            )
                    if node.name == "__init__":
                        self.assertEqual(ast.unparse(node.returns), "None")
                    if node.name == "__post_init__":
                        self.assertIn("value_object", path.parts)

    def test_external_transactions_and_no_direct_aggregate_writes(self) -> None:
        """Handlers/repositories не коммитят, а Application не присваивает состояние склада."""
        for path in MODULE.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(
                        node.func.attr,
                        ("commit", "rollback", "begin", "begin_nested"),
                        str(path),
                    )
                if "application" in path.parts and isinstance(
                    node, (ast.Assign, ast.AnnAssign, ast.AugAssign)
                ):
                    targets = (
                        node.targets if isinstance(node, ast.Assign) else [node.target]
                    )
                    for target in targets:
                        if isinstance(target, ast.Attribute):
                            self.assertTrue(
                                isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                                and target.attr.startswith("_"),
                                str(path),
                            )
        mapper = MODULE / "infrastructure/warehouse/persistence/mapper.py"
        tree = ast.parse(mapper.read_text())
        self.assertFalse(
            any(isinstance(node, (ast.If, ast.Raise)) for node in ast.walk(tree))
        )
        self.assertIn("Warehouse.restore", mapper.read_text())
        query = MODULE / "infrastructure/warehouse/persistence/query_repository.py"
        self.assertNotIn("WarehouseMapper", query.read_text())
        self.assertNotIn("restore(", query.read_text())

    def test_use_case_matrix_and_immutable_contracts(self) -> None:
        """Все три сценария имеют собственные файлы и конкретные возвращаемые DTO."""
        for scenario, kind, result in (
            ("create_warehouse", "command", "CreateWarehouseResultDTO"),
            ("get_warehouse", "query", "GetWarehouseDetailsDTO"),
            ("list_warehouses", "query", "ListWarehousesResultDTO"),
        ):
            directory = MODULE / "application/warehouse" / kind / scenario
            for name in (kind + ".py", "handler.py", "dto.py"):
                self.assertTrue((directory / name).is_file(), str(directory / name))
            methods = [
                node
                for node in ast.walk(ast.parse((directory / "handler.py").read_text()))
                if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute"
            ]
            self.assertEqual([ast.unparse(node.returns) for node in methods], [result])
            for relative in ("controller", "response"):
                self.assertTrue(
                    (
                        MODULE
                        / "presentation/warehouse/http"
                        / relative
                        / (scenario + ".py")
                    ).is_file()
                )
            request = (
                MODULE / "presentation/warehouse/http/request" / (scenario + ".py")
            )
            self.assertEqual(request.exists(), kind == "command")
            self.assertIn(
                "get_" + scenario + "_handler",
                (MODULE / "presentation/warehouse/depends.py").read_text(),
            )
        for path in MODULE.glob("application/warehouse/*/*/*.py"):
            if path.name in ("command.py", "query.py", "dto.py"):
                for node in ast.walk(ast.parse(path.read_text())):
                    if isinstance(node, ast.ClassDef):
                        self.assertTrue(
                            any(
                                isinstance(decorator, ast.Call)
                                and any(
                                    keyword.arg == "frozen"
                                    and isinstance(keyword.value, ast.Constant)
                                    and keyword.value.value is True
                                    for keyword in decorator.keywords
                                )
                                for decorator in node.decorator_list
                            ),
                            str(path),
                        )
        aggregate = ast.parse((MODULE / "domain/warehouse/aggregate.py").read_text())
        methods = {
            node.name
            for node in ast.walk(aggregate)
            if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue({"create", "restore"} <= methods)
        for path in MODULE.glob("presentation/**/router.py"):
            self.assertFalse(
                any(
                    isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    )
                    for node in ast.walk(ast.parse(path.read_text()))
                )
            )
