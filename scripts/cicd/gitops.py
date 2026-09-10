"""Git transactions. Release metadata lives in immutable annotated tags."""

from __future__ import annotations

from contextlib import contextmanager
import base64
import json
from pathlib import Path
import sys
import tempfile
import time

import yaml

from .common import (
    Error,
    RC,
    patch,
    run,
    set_chart_version,
    stable,
    versions,
    write_json,
)


class Repo:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def git(self, *args, check=True):
        return run("git", *args, cwd=self.root, check=check)

    def sha(self, ref="HEAD"):
        return self.git("rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()

    def exists(self, ref):
        return self.git("rev-parse", "--verify", ref, check=False).returncode == 0

    def branch(self):
        return self.git("symbolic-ref", "--short", "HEAD").stdout.strip()

    def ancestor(self, parent, child):
        result = self.git("merge-base", "--is-ancestor", parent, child, check=False)
        if result.returncode not in (0, 1):
            raise Error(result.stderr)
        return result.returncode == 0

    def clean(self):
        if self.git("status", "--porcelain").stdout:
            raise Error(
                "Commit or remove local changes first; resolve and commit any merge conflict"
            )

    def fetch(self):
        self.git("fetch", "origin", "--tags", "--prune")

    def tags(self, pattern):
        return self.git("tag", "--list", pattern).stdout.splitlines()

    def metadata(self, tag):
        raw = self.git(
            "for-each-ref", "--format=%(contents)", f"refs/tags/{tag}"
        ).stdout
        try:
            if raw.strip().startswith("dnk-cicd:"):
                raw = base64.b64decode(raw.strip().removeprefix("dnk-cicd:")).decode()
            data = json.loads(raw)
        except ValueError as error:
            raise Error(f"Tag {tag} has no valid CI/CD metadata") from error
        if not isinstance(data, dict) or data.get("schema") != 1:
            raise Error(f"Unsupported tag metadata: {tag}")
        return data

    def stable_tags(self, ref="HEAD"):
        result = []
        for tag in self.tags("v*"):
            try:
                number = stable(tag[1:])
            except Error:
                continue
            if self.ancestor(tag, ref):
                result.append((number, tag))
        return [tag for _, tag in sorted(result)]

    def chart_at(self, ref):
        content = self.git("show", f"{ref}:helm/Chart.yaml").stdout
        return str(yaml.safe_load(content)["version"])

    def local_branch(self, name):
        remote = f"origin/{name}"
        if not self.exists(f"refs/heads/{name}"):
            self.git("branch", name, remote)
        if self.sha(name) != self.sha(remote):
            raise Error(f"Local {name} differs from {remote}; synchronize it first")

    @contextmanager
    def checkout(self, ref):
        with tempfile.TemporaryDirectory(prefix="dnk-release-") as directory:
            path = Path(directory) / "checkout"
            self.git("worktree", "add", "--detach", str(path), ref)
            try:
                yield Repo(path)
            finally:
                self.git("worktree", "remove", "--force", str(path))

    def bump(self, app, chart, metadata):
        tag = "v" + app
        if self.exists(f"refs/tags/{tag}"):
            if self.metadata(tag) != metadata or self.sha(tag) != self.sha():
                raise Error(f"Refusing to reuse unrelated tag {tag}")
            return tag
        set_chart_version(self.root, chart)
        run(
            sys.executable,
            "-m",
            "commitizen",
            "bump",
            app,
            "--yes",
            "--changelog",
            "--annotated-tag",
            "--annotated-tag-message",
            "dnk-cicd:"
            + base64.b64encode(json.dumps(metadata, sort_keys=True).encode()).decode(),
            cwd=self.root,
        )
        if versions(self.root) != (app, chart):
            raise Error("Commitizen produced inconsistent application/chart versions")
        return tag


def start_release(repo):
    repo.clean()
    repo.fetch()
    branch = repo.branch()
    if branch != "develop" and not branch.startswith("release/"):
        raise Error("Run make release from develop or an existing release branch")
    if not repo.ancestor("origin/main", "HEAD"):
        raise Error("Merge the current main into this branch and check locally first")
    if branch == "develop" and repo.sha() != repo.sha("origin/develop"):
        raise Error("Push the checked develop branch before make release")
    current_app, current_chart = versions(repo.root)
    previous = repo.stable_tags("origin/main")
    if branch.startswith("release/") and not repo.exists("refs/tags/v" + branch[8:]):
        app = branch[8:]
    elif not previous:
        app = current_app
    else:
        # --get-next includes both release changes and a newly merged main hotfix.
        app = run(
            sys.executable, "-m", "commitizen", "bump", "--get-next", cwd=repo.root
        ).stdout.strip()
    stable(app)
    if repo.exists("refs/tags/v" + app):
        raise Error(f"Stable tag v{app} already exists; no new releasable changes")
    target = "release/" + app
    marker = "release-start/" + app
    remote_releases = repo.git(
        "for-each-ref", "--format=%(refname:strip=3)", "refs/remotes/origin/release/"
    ).stdout.splitlines()
    for active in remote_releases:
        if (
            active != target
            and active != branch
            and not repo.exists("refs/tags/v" + active[8:])
        ):
            raise Error(f"Finish the active {active} before starting another release")
    if branch != target and (
        repo.exists("refs/heads/" + target)
        or repo.exists("refs/remotes/origin/" + target)
    ):
        raise Error(
            f"Switch to the existing {target}; its history will not be replaced"
        )
    if not repo.exists("refs/tags/" + marker):
        base = repo.chart_at(previous[-1]) if previous else current_chart
        stable(base)
        metadata = {
            "schema": 1,
            "kind": "start",
            "source_sha": repo.sha(),
            "app_version": app,
            "chart_base": base,
        }
        repo.git("tag", "-a", marker, "-m", json.dumps(metadata, sort_keys=True))
    else:
        metadata = repo.metadata(marker)
        if metadata.get("kind") != "start" or not repo.ancestor(
            metadata["source_sha"], "HEAD"
        ):
            raise Error("Existing release start does not belong to this history")
    if branch != target:
        repo.git("switch", "-c", target)
    repo.git(
        "push", "--atomic", "--set-upstream", "origin", target, "refs/tags/" + marker
    )
    print(f"Published {target}; GitHub Actions will create its prereleases")


def release_sources(repo, branch):
    app = branch.removeprefix("release/")
    stable(app)
    metadata = repo.metadata("release-start/" + app)
    start = metadata["source_sha"]
    head = repo.sha("origin/" + branch)
    if metadata.get("kind") != "start" or not repo.ancestor(start, head):
        raise Error(
            "Release history no longer contains its start; force-push is unsupported"
        )
    return [start] + repo.git(
        "rev-list", "--reverse", "--topo-order", f"{start}..{head}"
    ).stdout.splitlines()


def rc_tags(repo, app):
    result = []
    for tag in repo.tags(f"v{app}-rc.*"):
        match = RC.fullmatch(tag)
        if not match:
            raise Error(f"Unexpected RC tag {tag}")
        result.append((int(match[2]), tag, repo.metadata(tag)))
    return sorted(result)


def prepare_rc(repo, branch, source):
    app = branch[8:]
    tags = rc_tags(repo, app)
    for _, tag, metadata in tags:
        if metadata.get("source_sha") == source and metadata.get("kind") == "rc":
            # A crash before push can leave a local tag: publish it before proceeding.
            repo.git("push", "origin", "refs/tags/" + tag)
            return tag
    number = max((n for n, _, _ in tags), default=0) + 1
    start = repo.metadata("release-start/" + app)
    stable_ancestors = repo.stable_tags(source)
    base = (
        repo.chart_at(stable_ancestors[-1]) if stable_ancestors else start["chart_base"]
    )
    chart = patch(base) + f"-rc.{number}"
    version = app + f"-rc.{number}"
    metadata = {
        "schema": 1,
        "kind": "rc",
        "branch": branch,
        "source_sha": source,
        "app_version": version,
        "chart_version": chart,
    }
    with repo.checkout(source) as checkout:
        tag = checkout.bump(version, chart, metadata)
        checkout.git("push", "origin", "refs/tags/" + tag)
    return tag


def wait_prerelease(repo, github, branch, source, timeout=3600):
    deadline = time.monotonic() + timeout
    while True:
        repo.fetch()
        for _, tag, metadata in rc_tags(repo, branch[8:]):
            if metadata.get("source_sha") != source:
                continue
            publication = github.get_release(tag)
            if (
                publication
                and publication["isPrerelease"]
                and not publication["isDraft"]
            ):
                return tag, metadata
        if time.monotonic() >= deadline:
            raise Error(
                "Prerelease is not ready; inspect Actions and retry make publish"
            )
        print("Waiting for the current HEAD prerelease...", flush=True)
        time.sleep(10)


def publish(repo, github, check):
    """Resume a durable local transaction; network writes happen only at atomic push."""
    journal = Path(
        repo.git("rev-parse", "--git-path", "cicd-publish.json").stdout.strip()
    )
    if not journal.is_absolute():
        journal = repo.root / journal
    repo.clean()
    repo.fetch()
    if journal.exists():
        state = json.loads(journal.read_text())
    else:
        branch, source = repo.branch(), repo.sha()
        if not branch.startswith(("release/", "hotfix/")):
            raise Error("Run make publish from release/* or a hotfix/* based on main")
        for name in ("main", "develop"):
            repo.local_branch(name)
        if not repo.ancestor("origin/main", source):
            raise Error("Merge the current main into this branch first")
        previous = repo.stable_tags("origin/main")
        if previous:
            release = github.get_release(previous[-1])
            if not release or release["isDraft"] or release["isPrerelease"]:
                raise Error(
                    f"Finish artifact publication for {previous[-1]} first; "
                    "rerun its main workflow to publish the GitHub Release"
                )
        if branch.startswith("release/"):
            if source != repo.sha("origin/" + branch):
                raise Error("Push the release HEAD before make publish")
            merge_ref, metadata = wait_prerelease(repo, github, branch, source)
            if not repo.ancestor("origin/main", source):
                raise Error(
                    "Main changed while waiting; merge it into release and publish a new RC"
                )
            app, chart = branch[8:], metadata["chart_version"].split("-", 1)[0]
            base = (
                repo.chart_at(previous[-1])
                if previous
                else repo.metadata("release-start/" + app)["chart_base"]
            )
            if chart != patch(base):
                raise Error(
                    "RC chart reservation is stale; merge main, run make release and wait for its RC"
                )
        else:
            for marker in repo.tags("release-start/*"):
                start = repo.metadata(marker)["source_sha"]
                if repo.ancestor(start, source) and not repo.ancestor(
                    start, "origin/main"
                ):
                    raise Error(
                        "This hotfix contains an active release; merge it into that release instead"
                    )
            if not previous or repo.sha(previous[-1]) != repo.sha("origin/main"):
                raise Error("A production hotfix requires a finalized main release")
            if source == repo.sha("origin/main"):
                raise Error("Hotfix has no changes")
            app, chart = patch(previous[-1][1:]), patch(repo.chart_at(previous[-1]))
            merge_ref = source
        stable(app)
        if repo.exists("refs/tags/v" + app):
            raise Error(f"Stable v{app} already exists")
        state = {
            "schema": 1,
            "source_branch": branch,
            "source_sha": source,
            "merge_ref": merge_ref,
            "app": app,
            "chart": chart,
            "base_main": repo.sha("origin/main"),
            "base_develop": repo.sha("origin/develop"),
            "phase": "merge",
        }
        write_json(journal, state)
    tag = "v" + state["app"]
    # Recover a successful push even if the process died before deleting its journal.
    if (
        state.get("develop_sha")
        and repo.sha("origin/main") == state["main_sha"]
        and repo.sha("origin/develop") == state["develop_sha"]
    ):
        if repo.sha(tag) != state["main_sha"]:
            raise Error("Published tag differs from the prepared transaction")
        journal.unlink()
        print(f"{tag} was already pushed successfully")
        return
    for name in ("main", "develop"):
        if repo.sha("origin/" + name) != state["base_" + name]:
            raise Error(
                f"origin/{name} changed during publication; preserve the journal and reconcile locally"
            )
    metadata = {
        "schema": 1,
        "kind": "stable",
        "branch": "main",
        "source_sha": state["source_sha"],
        "app_version": state["app"],
        "chart_version": state["chart"],
    }
    if state["phase"] == "merge":
        repo.git("switch", "main")
        if not repo.ancestor(state["merge_ref"], "HEAD"):
            repo.git("merge", "--no-ff", "--no-edit", state["merge_ref"])
        repo.bump(state["app"], state["chart"], metadata)
        state.update(phase="check", main_sha=repo.sha())
        write_json(journal, state)
    if state["phase"] == "check":
        repo.git("switch", "main")
        if repo.sha() != state["main_sha"]:
            raise Error(
                "Prepared main changed; refusing to publish an unchecked version"
            )
        check()
        repo.clean()
        state["phase"] = "backmerge"
        write_json(journal, state)
    if state["phase"] == "backmerge":
        repo.git("switch", "develop")
        if not repo.ancestor(state["main_sha"], "HEAD"):
            repo.git("merge", "--no-ff", "--no-edit", state["main_sha"])
        state.update(phase="push", develop_sha=repo.sha())
        write_json(journal, state)
    if (
        repo.sha("main") != state["main_sha"]
        or repo.sha("develop") != state["develop_sha"]
        or repo.sha(tag) != state["main_sha"]
    ):
        raise Error("Prepared refs changed; refusing to publish")
    repo.git("push", "--atomic", "origin", "main", "develop", "refs/tags/" + tag)
    journal.unlink()
    print(f"Published {tag}; follow artifact publication in GitHub Actions")
