"""Entry point: python -m scripts.cicd --help."""

import argparse
import json
import os
from pathlib import Path
import sys

from .artifacts import (
    GitHub,
    current_publication,
    publish_artifacts,
    publish_channel_aliases,
)
from .checks import check
from .common import Error, ROOT, stable, versions, write_json
from .gitops import Repo, prepare_rc, publish, release_sources, start_release


def ci(repo, github, branch, sha, output):
    if branch not in ("develop", "main") and not branch.startswith("release/"):
        raise Error("Only develop, main and release/* are publication branches")
    repo.fetch()
    run_id, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    if not run_id.isdecimal() or not attempt.isdecimal():
        raise Error("Run id and attempt must be numeric")
    if branch.startswith("release/"):
        if repo.exists("refs/tags/v" + branch[8:]):
            print("Release is finalized; no further RC tags will be created")
            return
        for source in release_sources(repo, branch):
            tag = prepare_rc(repo, branch, source)
            record = publish_artifacts(repo, tag, branch, source, run_id, attempt)
            changelog = repo.git("show", tag + ":CHANGELOG.md").stdout
            github.publish(tag, record, changelog)
        return
    if branch == "main":
        with repo.checkout(sha) as checkout:
            app, chart = versions(checkout.root)
            stable(app)
            stable(chart)
        tag = "v" + app
        if not repo.exists("refs/tags/" + tag) or repo.sha(tag) != repo.sha(sha):
            raise Error(
                "Main push must point at the stable tag produced by make publish"
            )
        metadata = repo.metadata(tag)
        if (
            metadata.get("kind") != "stable"
            or metadata.get("app_version") != app
            or metadata.get("chart_version") != chart
        ):
            raise Error("Main tag metadata does not match the versioned files")
        source = metadata["source_sha"]
    else:
        source = sha
    record = publish_artifacts(repo, sha, branch, source, run_id, attempt)
    write_json(output, record)
    if branch == "main":
        github.publish(
            tag,
            record,
            repo.git("show", sha + ":CHANGELOG.md").stdout,
            latest=current_publication(repo, record),
        )
    publish_channel_aliases(repo, record)
    print(json.dumps(record, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
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
    repo = Repo(ROOT)
    github = GitHub(os.environ.get("GITHUB_REPOSITORY", "dinikon/dnk-runtime-core"))
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
        print(f"CI/CD: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
