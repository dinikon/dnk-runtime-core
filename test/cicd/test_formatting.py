"""Black исправляет исходники, а проверка сохраняет рабочее дерево неизменным."""

from pathlib import Path
import tempfile
import unittest

from scripts.cicd.common import Error
from scripts.cicd.formatting import PYTHON_PATHS, format_python


class FormattingTests(unittest.TestCase):
    """Проверяет настоящий Black на изолированных исходниках."""

    def test_check_is_read_only_and_format_is_idempotent(self) -> None:
        """Все проверяемые каталоги исправляются одной командой без повторных правок."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for name in PYTHON_PATHS:
                path = root / name / "example.py"
                path.parent.mkdir()
                path.write_text("value=  1\n")
                paths.append(path)
            with self.assertRaisesRegex(Error, "make format"):
                format_python(root, check=True)
            self.assertTrue(all(path.read_text() == "value=  1\n" for path in paths))
            format_python(root)
            self.assertTrue(all(path.read_text() == "value = 1\n" for path in paths))
            format_python(root, check=True)
            format_python(root)
            self.assertTrue(all(path.read_text() == "value = 1\n" for path in paths))

    def test_syntax_error_is_not_ignored(self) -> None:
        """Ошибка разбора останавливает подготовку вместо пропуска проверки."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "src" / "invalid.py"
            path.parent.mkdir()
            path.write_text("def broken(:\n")
            with self.assertRaises(Error):
                format_python(root)
