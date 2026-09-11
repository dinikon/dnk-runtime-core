"""Git operations and Commitizen versioning in disposable worktrees."""

from __future__ import annotations

from contextlib import contextmanager
import base64
import json
from pathlib import Path
import sys
import tempfile

import yaml

from .common import (
    Error,
    run,
    set_chart_version,
    stable,
    versions,
)


class Repo:
    """Access repository refs and create versioned commits without shell interpolation."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def git(self, *args, check=True):
        """Run Git in this repository and return captured output."""
        return run("git", *args, cwd=self.root, check=check)

    def sha(self, ref="HEAD"):
        """Resolve a branch or annotated tag to its commit SHA."""
        return self.git("rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()

    def exists(self, ref):
        """Check whether a Git reference resolves."""
        return self.git("rev-parse", "--verify", ref, check=False).returncode == 0

    def branch(self):
        """Return the current branch; a detached HEAD is an error."""
        return self.git("symbolic-ref", "--short", "HEAD").stdout.strip()

    def ancestor(self, parent, child):
        """Check ancestry while distinguishing a negative result from a Git failure."""
        result = self.git("merge-base", "--is-ancestor", parent, child, check=False)
        if result.returncode not in (0, 1):
            raise Error(result.stderr)
        return result.returncode == 0

    def clean(self):
        """Require a clean working tree before changing release refs."""
        if self.git("status", "--porcelain").stdout:
            raise Error(
                "Commit or remove local changes first; resolve and commit any merge conflict"
            )

    def fetch(self):
        """Refresh origin branches and tags without rewriting local branches."""
        self.git("fetch", "origin", "--tags", "--prune")

    def tags(self, pattern):
        """List local tags matching a Git wildcard."""
        return self.git("tag", "--list", pattern).stdout.splitlines()

    def metadata(self, tag):
        """Decode and validate the versioned release metadata stored in a tag."""
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
        """Return stable tags reachable from ref in SemVer order."""
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
        """Read the chart version at a ref without checking out that ref."""
        content = self.git("show", f"{ref}:helm/Chart.yaml").stdout
        return str(yaml.safe_load(content)["version"])

    def local_branch(self, name):
        """Create a missing local branch or require it to match origin."""
        remote = f"origin/{name}"
        if not self.exists(f"refs/heads/{name}"):
            self.git("branch", name, remote)
        if self.sha(name) != self.sha(remote):
            raise Error(f"Local {name} differs from {remote}; synchronize it first")

    @contextmanager
    def checkout(self, ref):
        """Yield a detached temporary worktree and remove it even on failure."""
        with tempfile.TemporaryDirectory(prefix="dnk-release-") as directory:
            path = Path(directory) / "checkout"
            self.git("worktree", "add", "--detach", str(path), ref)
            try:
                yield Repo(path)
            finally:
                self.git("worktree", "remove", "--force", str(path))

    def bump(self, app, chart, metadata):
        """Run Commitizen once and refuse to reuse an unrelated version tag."""
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
