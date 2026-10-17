"""Архитектурные контракты среза профиля и tenant-persistence пользователя."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    "src/modules/identity/application/user",
    "src/modules/identity/domain/user",
    "src/modules/identity/infrastructure/user",
    "src/modules/identity/presentation/user",
)
EXTRA_FILES = (
    "src/modules/identity/infrastructure/persistence/models/user.py",
    "src/modules/identity/infrastructure/cloud/bootstrap.py",
    "src/modules/identity/application/auth/service/session_authentication.py",
    "src/modules/identity/application/auth/service/session_issuer.py",
    "src/modules/identity/application/invitation/command/accept_invitation/handler.py",
    "src/modules/tenancy/infrastructure/tenant/persistence/tenant_connection.py",
    "migrations/tenant/versions/0025_user_display_currency.py",
)


class CurrencyProfileArchitectureTests(unittest.TestCase):
    def test_annotations_docstrings_factories_and_imports(self) -> None:
        paths = {ROOT / file for file in EXTRA_FILES} | {
            file for folder in DIRECTORIES for file in (ROOT / folder).rglob("*.py")
        }
        for path in sorted(paths):
            with self.subTest(path=str(path)):
                if path.name == "__init__.py":
                    self.assertEqual(path.read_text().strip(), "")
                tree = ast.parse(path.read_text())
                internal = any(
                    layer in str(path) for layer in ("/application/", "/domain/")
                )
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
                            if arg.arg not in {"self", "cls"}:
                                self.assertIsNotNone(
                                    arg.annotation, f"{node.name}:{arg.arg}"
                                )
                        if node.name == "__post_init__":
                            self.assertIn("/value_object/", str(path))
                    imports = (
                        [item.name for item in node.names]
                        if isinstance(node, ast.Import)
                        else (
                            [node.module]
                            if isinstance(node, ast.ImportFrom) and node.module
                            else []
                        )
                    )
                    for name in imports:
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
                            self.assertNotIn(".infrastructure", name)
                            self.assertNotIn(".presentation", name)
                        if "/domain/" in str(path):
                            self.assertNotIn(".application", name)
                        if name.startswith("src.modules"):
                            self.assertTrue(
                                (ROOT / (name.replace(".", "/") + ".py")).is_file(),
                                name,
                            )
                    if isinstance(node, ast.Call) and isinstance(
                        node.func, ast.Attribute
                    ):
                        # Explicit commit remains necessary in invitation acceptance before session issuance.
                        if not str(path).endswith(
                            "invitation/command/accept_invitation/handler.py"
                        ):
                            self.assertNotIn(
                                node.func.attr, ("commit", "rollback"), str(path)
                            )
        from src.modules.identity.domain.user.aggregate import User
        from src.modules.identity.domain.user.entity import UserEmail

        for model in (User, UserEmail):
            self.assertTrue(callable(model.create))
            self.assertTrue(callable(model.restore))

    def test_scenario_contracts_and_tenant_binding_are_explicit(self) -> None:
        for kind, scenario in (
            ("command", "update_current_user_profile"),
            ("query", "get_current_user"),
        ):
            base = ROOT / "src/modules/identity/application/user" / kind / scenario
            for name in (kind + ".py", "handler.py", "dto.py", "email_dto.py"):
                self.assertTrue((base / name).is_file())
            self.assertNotIn("host:", (base / (kind + ".py")).read_text())
            self.assertNotIn("session_token:", (base / (kind + ".py")).read_text())
            self.assertTrue(
                (
                    ROOT
                    / f"src/modules/identity/presentation/user/http/response/{scenario}.py"
                ).is_file()
            )
        self.assertFalse(
            (
                ROOT
                / "src/modules/identity/presentation/user/http/response/current_user.py"
            ).exists()
        )
        for filename in ("repository.py", "query_repository.py"):
            content = (
                ROOT / "src/modules/identity/infrastructure/user/persistence" / filename
            ).read_text()
            self.assertNotIn("schema_translate_map=", content)
            self.assertIn("require_tenant_schema", content)
        query = (
            ROOT
            / "src/modules/identity/infrastructure/user/persistence/query_repository.py"
        ).read_text()
        self.assertNotIn("UserMapper", query)
        self.assertNotIn(".restore(", query)
        from src.modules.identity.infrastructure.persistence.models.user import (
            UserModel,
        )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
            TenantBase,
        )

        self.assertIs(UserModel.metadata, TenantBase.metadata)
        self.assertEqual(UserModel.__table__.schema, "tenant")
        self.assertEqual(UserModel.__table__.c.display_currency.type.length, 3)
        self.assertTrue(UserModel.__table__.c.display_currency.nullable)
