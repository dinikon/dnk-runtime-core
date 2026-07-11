import ast
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = CONTROL_PLANE_ROOT.parent


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


class ControlPlaneArchitectureBoundaryTests(unittest.TestCase):
    def test_control_plane_does_not_import_runtime_src_package(self) -> None:
        violations: list[str] = []
        for path in (CONTROL_PLANE_ROOT / "src" / "control_plane").rglob("*.py"):
            for module in _imported_modules(path):
                if module == "src" or module.startswith("src."):
                    violations.append(f"{path.relative_to(REPOSITORY_ROOT)}: {module}")

        self.assertEqual(violations, [])

    def test_runtime_does_not_import_control_plane_package(self) -> None:
        violations: list[str] = []
        for path in (REPOSITORY_ROOT / "src").rglob("*.py"):
            for module in _imported_modules(path):
                if module == "control_plane" or module.startswith("control_plane."):
                    violations.append(f"{path.relative_to(REPOSITORY_ROOT)}: {module}")

        self.assertEqual(violations, [])

    def test_domain_and_application_do_not_import_outer_layers(self) -> None:
        violations: list[str] = []
        modules_root = CONTROL_PLANE_ROOT / "src" / "control_plane" / "modules"
        for path in modules_root.rglob("*.py"):
            if not ({"domain", "application"} & set(path.parts)):
                continue
            for module in _imported_modules(path):
                if ".infrastructure" in module or ".presentation" in module:
                    violations.append(
                        f"{path.relative_to(CONTROL_PLANE_ROOT)}: {module}"
                    )

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
