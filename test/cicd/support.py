"""Shared fake services and isolated Git/Commitizen fixtures."""

from pathlib import Path
from unittest.mock import patch as mock_patch
import hashlib
import json
import shutil
import tempfile
import unittest

import tomlkit
import yaml

from scripts.cicd.common import ROOT, run
from scripts.cicd.gitops import prepare_rc, publish, start_release
from scripts.cicd.registry import PUBLICATION
from scripts.cicd.repository import Repo


class Releases:
    def __init__(self):
        self.items = {}

    def get_release(self, tag):
        return self.items.get(tag)

    def ready(self, tag, prerelease=True):
        self.items[tag] = {"isPrerelease": prerelease, "isDraft": False}


class MemoryRegistry:
    def __init__(self):
        self.manifests = {}
        self.digests = {}
        self.chart_pushes = 0

    def save(self, ref, manifest):
        digest = (
            "sha256:"
            + hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        )
        self.manifests[ref] = manifest
        self.manifests[digest] = manifest
        self.digests[ref] = digest

    def manifest(self, ref):
        return self.manifests.get(ref)

    def digest(self, ref):
        return self.digests[ref]

    def alias(self, repository, digest, tag):
        self.save(repository + ":" + tag, self.manifests[digest])

    def push_chart(self, repository, archive, config, publication):
        self.chart_pushes += 1
        ref = repository + ":" + publication["chart_version"]
        self.save(ref, {"annotations": {PUBLICATION: json.dumps(publication)}})
        return self.digest(ref)


class ReleaseRepoTestCase(unittest.TestCase):
    """Provide a disposable repository whose only remote is a local bare repo."""

    def setUp(self):
        self.enterContext(mock_patch("scripts.cicd.registry.time.sleep"))
        self.temporary = tempfile.TemporaryDirectory(prefix="dnk-git-test-")
        self.addCleanup(self.temporary.cleanup)
        parent = Path(self.temporary.name)
        self.root = parent / "repo"
        self.root.mkdir()
        remote = parent / "origin.git"
        run("git", "init", "--bare", remote)
        self.repo = Repo(self.root)
        self.repo.git("init", "-b", "main")
        self.repo.git("config", "user.name", "Local release test")
        self.repo.git("config", "user.email", "test@example.invalid")
        self.repo.git("config", "commit.gpgsign", "false")
        self.repo.git("config", "tag.gpgsign", "false")
        for name in ("pyproject.toml", "uv.lock", "docker-bake.hcl"):
            shutil.copy2(ROOT / name, self.root / name)
        shutil.copytree(
            ROOT / "helm",
            self.root / "helm",
            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
        )
        # Start from an unreleased fixture, even when checks run on an RC/stable
        # checkout. Copying its versions would change every expected release.
        project_path = self.root / "pyproject.toml"
        project = tomlkit.parse(project_path.read_text())
        project["project"]["version"] = "0.1.0"
        project_path.write_text(tomlkit.dumps(project))
        lock_path = self.root / "uv.lock"
        lock = tomlkit.parse(lock_path.read_text())
        for package in lock["package"]:
            if package["name"] == project["project"]["name"]:
                package["version"] = "0.1.0"
                break
        else:
            self.fail("Application package is missing from the fixture lockfile")
        lock_path.write_text(tomlkit.dumps(lock))
        chart_path = self.root / "helm/Chart.yaml"
        chart = yaml.safe_load(chart_path.read_text())
        chart.update(version="0.3.2", appVersion="0.1.0")
        chart_path.write_text(yaml.safe_dump(chart, sort_keys=False))
        (self.root / ".gitignore").write_text("__pycache__/\n.venv/\n")
        self.commit("chore: initial repository", "base.txt")
        self.repo.git("remote", "add", "origin", remote)
        self.repo.git("push", "-u", "origin", "main")
        self.repo.git("switch", "-c", "develop")
        self.commit("feat: initial feature", "feature.txt")
        self.repo.git("push", "-u", "origin", "develop")
        self.github = Releases()

    def commit(self, message, filename="change.txt", text=None):
        (self.root / filename).write_text(text or message)
        self.repo.git("add", ".")
        self.repo.git("commit", "-m", message)
        return self.repo.sha()

    def rc(self, branch=None):
        branch = branch or self.repo.branch()
        self.repo.git("push", "origin", branch)
        self.repo.fetch()
        tag = prepare_rc(self.repo, branch, self.repo.sha())
        self.github.ready(tag)
        return tag

    def initial_release(self):
        start_release(self.repo)
        self.rc()
        publish(self.repo, self.github, lambda: None)
        self.github.ready("v0.1.0", prerelease=False)
