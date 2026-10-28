"""Единое форматирование Python для локальной разработки и подготовки версий."""

from pathlib import Path
import sys

from .common import Error, live
from .observability import stage

PYTHON_PATHS = ("src", "test", "migrations", "scripts")


def format_python(root: Path, *, check: bool = False) -> None:
    """Форматирует исходники Black или проверяет их без изменения файлов."""
    paths = [name for name in PYTHON_PATHS if (root / name).is_dir()]
    if not paths:
        return
    with stage("Python formatting" if check else "Format Python"):
        try:
            live(
                sys.executable,
                "-m",
                "black",
                *(("--check",) if check else ()),
                *paths,
                cwd=root,
            )
        except Error as error:
            if check:
                raise Error(
                    "Python formatting failed; run make format, review and commit "
                    "the changes, then retry"
                ) from error
            raise
