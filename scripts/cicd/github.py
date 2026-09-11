"""Read release readiness via REST and publish release notes via GitHub CLI."""

import json
import os
from pathlib import Path
import tempfile
from urllib.parse import quote

import httpx

from .common import Error, run
from .observability import logger


class GitHub:
    """GitHub release readiness and idempotent publication for one repository."""

    def __init__(self, repository):
        self.repository = repository

    def get_release(self, tag):
        """Read release readiness without requiring GitHub CLI locally."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        url = "https://api.github.com/repos/" + self.repository
        try:
            with httpx.Client(
                headers=headers, timeout=30, follow_redirects=True
            ) as client:
                result = client.get(url + "/releases/tags/" + quote(tag, safe=""))
                if result.status_code == 404:
                    # The tag endpoint only promises published releases. Listing
                    # also finds drafts and distinguishes missing releases from
                    # inaccessible repositories, which GitHub also hides as 404.
                    page = 1
                    while True:
                        result = client.get(
                            url + "/releases", params={"per_page": 100, "page": page}
                        )
                        result.raise_for_status()
                        release = next(
                            (item for item in result.json() if item["tag_name"] == tag),
                            None,
                        )
                        if release is not None:
                            break
                        if "next" not in result.links:
                            return None
                        page += 1
                else:
                    result.raise_for_status()
                    release = result.json()
        except httpx.HTTPStatusError as error:
            raise Error(
                f"GitHub release lookup failed (HTTP {error.response.status_code}); "
                "check GITHUB_REPOSITORY, GH_TOKEN or GITHUB_TOKEN with Contents: read "
                "access, and GitHub API rate limits"
            ) from error
        except httpx.RequestError as error:
            raise Error(
                "GitHub release lookup failed; check the network connection and retry"
            ) from error
        return {
            "isDraft": release["draft"],
            "isPrerelease": release["prerelease"],
            "tagName": release["tag_name"],
            "body": release.get("body") or "",
        }

    def publish(self, tag, record, changelog, *, latest=False):
        """Publish ready artifacts as a Release without rewriting published notes."""
        logger.info("Checking GitHub release: %s", tag)
        prerelease = record["channel"] == "rc"
        body = f"{changelog.strip()}\n\n### Artifacts\n\n```json\n{json.dumps(record, indent=2)}\n```\n"
        existing = self.get_release(tag)
        if existing:
            if existing["isPrerelease"] != prerelease:
                raise Error("Existing GitHub release has a different release type")
            if not existing["isDraft"]:
                logger.info("Reusing published GitHub release: %s", tag)
                return
        with tempfile.TemporaryDirectory(prefix="dnk-release-notes-") as temporary:
            notes = Path(temporary) / "notes.md"
            notes.write_text(body)
            if existing:
                run(
                    "gh",
                    "release",
                    "edit",
                    tag,
                    "--repo",
                    self.repository,
                    "--notes-file",
                    notes,
                    "--draft=false",
                    "--latest" if latest and not prerelease else "--latest=false",
                )
            else:
                run(
                    "gh",
                    "release",
                    "create",
                    tag,
                    "--repo",
                    self.repository,
                    "--verify-tag",
                    "--title",
                    tag,
                    "--notes-file",
                    notes,
                    "--latest" if latest and not prerelease else "--latest=false",
                    "--draft=false",
                    *(["--prerelease"] if prerelease else []),
                )
        logger.info("GitHub release ready: %s", tag)
