#!/usr/bin/env python
"""Run management commands for the standalone Core project."""

import os
import sys


def main():
    """Configure Django and dispatch a management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dnk_core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Install the Core dependencies with "
            "`uv sync --frozen` from the core directory."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
