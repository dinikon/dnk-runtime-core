"""Publish supported branches while preserving release and alias ordering."""

import json
import os

from .aliases import current_publication, publish_channel_aliases
from .artifacts import publish_artifacts
from .common import Error, stable, versions, write_json
from .gitops import prepare_rc, release_sources
from .observability import log_context, logger, stage


def stable_source(repo, sha):
    """Validate the stable tag and recover its original release/hotfix source SHA."""
    with repo.checkout(sha) as checkout:
        app, chart = versions(checkout.root)
        stable(app)
        stable(chart)
    tag = "v" + app
    if not repo.exists("refs/tags/" + tag) or repo.sha(tag) != repo.sha(sha):
        raise Error("Main push must point at the stable tag produced by make publish")
    metadata = repo.metadata(tag)
    if (
        metadata.get("kind") != "stable"
        or metadata.get("app_version") != app
        or metadata.get("chart_version") != chart
    ):
        raise Error("Main tag metadata does not match the versioned files")
    return tag, metadata["source_sha"]


def publish_rcs(repo, github, branch, run_id, attempt, output):
    """Drain release history in order, saving each artifact record before its Release."""
    if repo.exists("refs/tags/v" + branch[8:]):
        logger.info("Release is finalized; no further RC tags will be created")
        return
    sources = release_sources(repo, branch)
    logger.info("Processing %s release source commits", len(sources))
    for position, source in enumerate(sources, 1):
        with stage(
            "Publish release candidate",
            source_sha=source,
            position=f"{position}/{len(sources)}",
        ):
            with stage("Prepare RC tag"):
                tag = prepare_rc(repo, branch, source)
            with log_context(tag=tag):
                record = publish_artifacts(repo, tag, branch, source, run_id, attempt)
                # Keep earlier records when a later RC or GitHub API call fails.
                write_json(output.parent / "publications" / f"{tag}.json", record)
                write_json(output, record)
                with stage("Publish GitHub prerelease"):
                    changelog = repo.git("show", tag + ":CHANGELOG.md").stdout
                    github.publish(tag, record, changelog)


def ci(repo, github, branch, sha, output):
    """Publish artifacts, then GitHub Releases, then pointers for the current HEAD.

    A release branch is processed sequentially to retain the RC numbering contract.
    Re-runs reuse immutable artifacts and cannot move a stale branch's aliases.
    """
    run_id = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ["GITHUB_RUN_ATTEMPT"]
    with log_context(branch=branch, sha=sha, run_id=run_id, attempt=attempt):
        with stage("Validate publication request"):
            if branch not in ("develop", "main") and not branch.startswith("release/"):
                raise Error("Only develop, main and release/* are publication branches")
            if not run_id.isdecimal() or not attempt.isdecimal():
                raise Error("Run id and attempt must be numeric")
            repo.fetch()
        if branch.startswith("release/"):
            publish_rcs(repo, github, branch, run_id, attempt, output)
            return
        source = sha
        if branch == "main":
            with stage("Validate stable tag"):
                tag, source = stable_source(repo, sha)
        with stage("Publish versioned artifacts", source_sha=source):
            record = publish_artifacts(repo, sha, branch, source, run_id, attempt)
            write_json(output, record)
        if branch == "main":
            with stage("Publish GitHub release", tag=tag):
                github.publish(
                    tag,
                    record,
                    repo.git("show", sha + ":CHANGELOG.md").stdout,
                    latest=current_publication(repo, record),
                )
        with stage("Update channel aliases"):
            publish_channel_aliases(repo, record)
        print(json.dumps(record, indent=2), flush=True)
