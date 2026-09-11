"""Entry point: python -m scripts.cicd --help."""

import argparse
import os
from pathlib import Path
import sys

from .checks import check
from .common import Error, ROOT
from .github import GitHub
from .gitops import publish, start_release
from .observability import configure_logging, log_context, logger
from .pipeline import ci
from .repository import Repo


def main():
    """Parse CLI options and translate actionable failures into a nonzero exit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    checks = commands.add_parser("check")
    checks.add_argument("--full", action="store_true")
    commands.add_parser("release")
    commands.add_parser("publish")
    workflow = commands.add_parser("ci")
    workflow.add_argument("--branch", required=True)
    workflow.add_argument("--sha", required=True)
    workflow.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    configure_logging(args.log_level)
    repo = Repo(ROOT)
    github = GitHub(os.environ.get("GITHUB_REPOSITORY", "dinikon/dnk-runtime-core"))
    with log_context(command=args.command):
        try:
            if args.command == "check":
                check(ROOT, args.full)
            elif args.command == "release":
                start_release(repo)
            elif args.command == "publish":
                publish(repo, github, lambda: check(ROOT))
            elif args.command == "ci":
                ci(repo, github, args.branch, args.sha, args.output)
        except (Error, OSError, ValueError, KeyError) as error:
            logger.error("CI/CD: %s", error)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
