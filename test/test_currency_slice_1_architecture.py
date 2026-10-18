"""Архитектурные ограничения первого валютного среза дополняют функциональные тесты."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    "src/modules/reference_data/application/currency/query/validate_currency",
    "src/modules/tenancy/application/tenant/command/create_tenant",
    "src/modules/tenancy/application/tenant_currency_settings/query/get_tenant_currency_settings",
)
SUBSYSTEMS = (
    *SCENARIOS,
    "src/modules/reference_data/application/currency/port",
    "src/modules/reference_data/infrastructure/currency/persistence",
    "src/modules/tenancy/application/tenant/port",
    "src/modules/tenancy/application/tenant_currency_settings/port",
    "src/modules/tenancy/domain/tenant_currency_settings",
    "src/modules/tenancy/infrastructure/tenant_currency_settings",
    "src/modules/tenancy/presentation/tenant_currency_settings/http/controller",
    "src/modules/tenancy/presentation/tenant_currency_settings/http/response",
)
FILES = (
    "src/modules/tenancy/presentation/tenant_currency_settings/depends.py",
    "src/modules/tenancy/presentation/tenant_currency_settings/router.py",
    "src/modules/shared/domain/value_object/currency.py",
    "src/modules/shared/domain/value_object/money.py",
    "src/modules/shared/domain/value_object/money_error.py",
    "src/modules/tenancy/domain/tenant_currency_settings/aggregate.py",
    "src/modules/tenancy/domain/tenant_currency_settings/error.py",
    "src/modules/tenancy/application/tenant/onboarding.py",
    "src/modules/tenancy/infrastructure/adapter/currency_validator.py",
    "src/modules/tenancy/infrastructure/adapter/tenant_currency_settings.py",
    "src/modules/tenancy/infrastructure/persistence/models/tenant_currency_settings.py",
    "src/modules/tenancy/infrastructure/tenant_currency_settings/persistence/query_mapper.py",
    "src/modules/tenancy/infrastructure/tenant_currency_settings/persistence/query_repository.py",
)


def slice_files() -> set[Path]:
    return {ROOT / item for item in FILES} | {
        path for directory in SUBSYSTEMS for path in (ROOT / directory).rglob("*.py")
    }


class CurrencySliceOneArchitectureTests(unittest.TestCase):
    def test_scenario_files_packages_and_http_contract(self) -> None:
        for directory in SCENARIOS:
            scenario = ROOT / directory
            self.assertTrue((scenario / "handler.py").is_file())
            self.assertTrue((scenario / "dto.py").is_file())
            self.assertTrue(
                (
                    scenario
                    / ("command.py" if "/command/" in directory else "query.py")
                ).is_file()
            )
        for directory in SUBSYSTEMS:
            for package in (ROOT / directory).rglob("__init__.py"):
                self.assertEqual(package.read_text().strip(), "", str(package))
        http = ROOT / "src/modules/tenancy/presentation/tenant_currency_settings/http"
        self.assertTrue((http / "controller/get_tenant_currency_settings.py").is_file())
        self.assertTrue((http / "response/get_tenant_currency_settings.py").is_file())
        self.assertFalse((http / "request/get_tenant_currency_settings.py").exists())

    def test_annotations_docstrings_factories_and_vo_validation(self) -> None:
        for path in slice_files():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.assertIsNotNone(ast.get_docstring(node), f"{path}:{node.name}")
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                self.assertIsNotNone(ast.get_docstring(node), f"{path}:{node.name}")
                self.assertIsNotNone(node.returns, f"{path}:{node.name}")
                args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                args += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
                for arg in args:
                    if arg.arg not in {"self", "cls"}:
                        self.assertIsNotNone(
                            arg.annotation, f"{path}:{node.name}:{arg.arg}"
                        )
                if node.name == "__post_init__":
                    self.assertIn("/value_object/", str(path))
        from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
            TenantCurrencySettings,
        )

        self.assertTrue(callable(TenantCurrencySettings.create))
        self.assertTrue(callable(TenantCurrencySettings.restore))
        self.assertIsNone(TenantCurrencySettings.base_currency.fset)

    def test_dependencies_point_inward_and_transactions_stay_external(self) -> None:
        for path in slice_files():
            relative = str(path.relative_to(ROOT))
            tree = ast.parse(path.read_text())
            internal = "/application/" in relative or "/domain/" in relative
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if internal:
                        self.assertFalse(
                            name.startswith(
                                (
                                    "sqlalchemy",
                                    "fastapi",
                                    "pydantic",
                                    "httpx",
                                    "src.config",
                                )
                            ),
                            f"{path}:{name}",
                        )
                        self.assertNotIn(".infrastructure", name, f"{path}:{name}")
                        self.assertNotIn(".presentation", name, f"{path}:{name}")
                        if "/domain/" in relative:
                            self.assertNotIn(".application", name, f"{path}:{name}")
                    if name.startswith("src.modules"):
                        self.assertTrue(
                            (ROOT / (name.replace(".", "/") + ".py")).is_file(),
                            f"{path}:indirect import {name}",
                        )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, ("commit", "rollback"), str(path))
            if "/tenancy/application/" in relative:
                self.assertNotIn("src.modules.reference_data", path.read_text())
