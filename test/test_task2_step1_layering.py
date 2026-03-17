from __future__ import annotations

import ast
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = PROJECT_ROOT / "src" / "modules"
TARGET_MODULES: tuple[str, ...] = ("crm", "runtime_schema", "runtime_record")


def _module_files(module_name: str) -> list[Path]:
    return sorted((MODULES_ROOT / module_name).rglob("*.py"))


def _package_for_file(file_path: Path) -> str:
    rel = file_path.relative_to(PROJECT_ROOT).with_suffix("")
    parts = list(rel.parts)

    if parts[-1] == "__init__":
        package_parts = parts[:-1]
    else:
        package_parts = parts[:-1]

    return ".".join(package_parts)


def _resolved_import_targets(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    current_package = _package_for_file(file_path)
    current_parts = current_package.split(".") if current_package else []

    targets: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                targets.add(imported.name)
            continue

        if isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module:
                    targets.add(node.module)
                continue

            base_parts = list(current_parts)
            trim_count = node.level - 1
            if trim_count > 0:
                base_parts = base_parts[:-trim_count]

            module_parts = node.module.split(".") if node.module else []
            full_target = ".".join([*base_parts, *module_parts]).strip(".")
            if full_target:
                targets.add(full_target)

    return targets


def _assert_no_forbidden_imports(
    test_case: unittest.TestCase,
    *,
    module_name: str,
    files: list[Path],
    forbidden_prefixes: tuple[str, ...],
) -> None:
    for file_path in files:
        import_targets = _resolved_import_targets(file_path)

        for target in import_targets:
            for forbidden_prefix in forbidden_prefixes:
                with test_case.subTest(
                    module=module_name,
                    file=str(file_path.relative_to(PROJECT_ROOT)),
                    target=target,
                    forbidden=forbidden_prefix,
                ):
                    test_case.assertFalse(
                        target == forbidden_prefix
                        or target.startswith(f"{forbidden_prefix}."),
                        msg=(
                            "Forbidden import direction detected: "
                            f"{file_path.relative_to(PROJECT_ROOT)} -> {target}"
                        ),
                    )


class TestTask2Step1Layering(unittest.TestCase):
    def test_domain_does_not_import_application_infrastructure_or_presentation(
        self,
    ) -> None:
        for module_name in TARGET_MODULES:
            base = f"src.modules.{module_name}"
            files = [
                path
                for path in _module_files(module_name)
                if "/domain/" in path.as_posix()
            ]

            _assert_no_forbidden_imports(
                self,
                module_name=module_name,
                files=files,
                forbidden_prefixes=(
                    f"{base}.application",
                    f"{base}.infrastructure",
                    f"{base}.presentation",
                ),
            )

    def test_application_does_not_import_infrastructure_or_presentation(
        self,
    ) -> None:
        for module_name in TARGET_MODULES:
            base = f"src.modules.{module_name}"
            files = [
                path
                for path in _module_files(module_name)
                if "/application/" in path.as_posix()
            ]

            _assert_no_forbidden_imports(
                self,
                module_name=module_name,
                files=files,
                forbidden_prefixes=(
                    f"{base}.infrastructure",
                    f"{base}.presentation",
                ),
            )

    def test_presentation_http_does_not_import_infrastructure(self) -> None:
        for module_name in TARGET_MODULES:
            base = f"src.modules.{module_name}"
            files = [
                path
                for path in _module_files(module_name)
                if "/presentation/http/" in path.as_posix()
            ]

            _assert_no_forbidden_imports(
                self,
                module_name=module_name,
                files=files,
                forbidden_prefixes=(f"{base}.infrastructure",),
            )


if __name__ == "__main__":
    unittest.main()
