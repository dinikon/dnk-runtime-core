"""Проверки архитектурных контрактов нового валютного модуля и batch Query."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    "src/modules/currency",
    "src/modules/reference_data/application/currency/query/get_currency_validation_catalog",
)
FILES = (
    "src/modules/reference_data/application/currency/port/validation_catalog.py",
    "src/modules/reference_data/domain/currency/policy.py",
    "src/modules/reference_data/infrastructure/currency/persistence/validation_catalog_mapper.py",
    "src/modules/reference_data/infrastructure/currency/persistence/validation_catalog_repository.py",
    "src/management/commands/currency.py",
    "migrations/tenant/versions/0024_currency_exchange_rates.py",
)


class CurrencySliceTwoArchitectureTests(unittest.TestCase):
    def test_files_annotations_docstrings_and_dependency_direction(self) -> None:
        files = {ROOT / item for item in FILES} | {
            path
            for directory in DIRECTORIES
            for path in (ROOT / directory).rglob("*.py")
        }
        for path in files:
            with self.subTest(path=str(path)):
                if path.name == "__init__.py":
                    self.assertEqual(path.read_text().strip(), "")
                tree = ast.parse(path.read_text())
                internal = "/domain/" in str(path) or "/application/" in str(path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        self.assertIsNotNone(ast.get_docstring(node), node.name)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertIsNotNone(node.returns, node.name)
                        self.assertIsNotNone(ast.get_docstring(node), node.name)
                        args = (
                            node.args.posonlyargs
                            + node.args.args
                            + node.args.kwonlyargs
                            + [
                                arg
                                for arg in (node.args.vararg, node.args.kwarg)
                                if arg
                            ]
                        )
                        for arg in args:
                            if arg.arg not in ("self", "cls"):
                                self.assertIsNotNone(
                                    arg.annotation, f"{node.name}:{arg.arg}"
                                )
                        if node.name == "__post_init__":
                            self.assertIn("/value_object/", str(path))
                    names = []
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                    if isinstance(node, ast.ImportFrom) and node.module:
                        names = [node.module]
                    for name in names:
                        if internal:
                            self.assertFalse(
                                name.startswith(
                                    (
                                        "sqlalchemy",
                                        "httpx",
                                        "fastapi",
                                        "pydantic",
                                        "src.config",
                                    )
                                ),
                                name,
                            )
                            self.assertNotIn(".infrastructure.", name)
                            self.assertNotIn(".presentation.", name)
                            if "/domain/" in str(path):
                                self.assertNotIn(".application.", name)
                            if "/currency/application/" in str(
                                path
                            ) and "/reference_data/" not in str(path):
                                self.assertNotIn("src.modules.reference_data", name)
                        if name.startswith("src.modules"):
                            self.assertTrue(
                                (ROOT / (name.replace(".", "/") + ".py")).is_file(),
                                name,
                            )
                    if isinstance(node, ast.Call) and isinstance(
                        node.func, ast.Attribute
                    ):
                        self.assertNotIn(
                            node.func.attr, ("commit", "rollback"), str(path)
                        )
        # Только VO может валидироваться в __post_init__; агрегат использует фабрики.
        from src.modules.currency.domain.aggregate import ExchangeRateBook

        self.assertTrue(callable(ExchangeRateBook.create))
        self.assertTrue(callable(ExchangeRateBook.restore))
        self.assertTrue(callable(ExchangeRateBook.refresh))

    def test_scenarios_have_separate_contracts_and_no_refresh_http(self) -> None:
        for directory, input_file in (
            (
                "src/modules/currency/application/command/refresh_exchange_rates",
                "command.py",
            ),
            (
                "src/modules/reference_data/application/currency/query/get_currency_validation_catalog",
                "query.py",
            ),
        ):
            for filename in (input_file, "handler.py", "dto.py", "__init__.py"):
                self.assertTrue((ROOT / directory / filename).is_file())
        self.assertFalse(
            (ROOT / "src/modules/currency/domain/exchange_rate_book").exists()
        )
        self.assertFalse((ROOT / "src/modules/currency/presentation/http").exists())
        source = (
            ROOT / "src/modules/currency/infrastructure/nbu/source.py"
        ).read_text()
        self.assertNotIn("float(", source.split("def _retry_after")[0])
        self.assertNotIn("sqlalchemy", source)
        self.assertNotIn("session", source)
        migration = (
            ROOT / "migrations/tenant/versions/0024_currency_exchange_rates.py"
        ).read_text()
        self.assertNotIn("httpx", migration)
        self.assertNotIn("JSON", migration)

    def test_currency_models_are_tenant_local(self) -> None:
        from src.modules.currency.infrastructure.persistence.models.exchange_rate_book import (
            ExchangeRateBookModel,
        )
        from src.modules.currency.infrastructure.persistence.models.exchange_rate_quote import (
            ExchangeRateQuoteModel,
        )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
            TenantBase,
            TENANT_SCHEMA_ALIAS,
        )
        from src.modules.shared.infrastructure.persistence.base import Base

        for model in (ExchangeRateBookModel, ExchangeRateQuoteModel):
            self.assertIs(model.metadata, TenantBase.metadata)
            self.assertEqual(model.__table__.schema, TENANT_SCHEMA_ALIAS)
            self.assertNotIn("public." + model.__tablename__, Base.metadata.tables)
        foreign_key = next(iter(ExchangeRateQuoteModel.__table__.foreign_keys))
        self.assertIs(foreign_key.column.table, ExchangeRateBookModel.__table__)
