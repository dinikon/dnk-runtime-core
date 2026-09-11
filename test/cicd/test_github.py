"""GitHub REST readiness and idempotent Release publication."""

from unittest.mock import patch as mock_patch
import os
import unittest

import httpx

from scripts.cicd.common import Error
from scripts.cicd.github import GitHub


class GitHubReleaseTests(unittest.TestCase):
    def setUp(self):
        self.github = GitHub("owner/repo")
        self.requests = []
        self.responses = []
        self.release = {
            "draft": False,
            "prerelease": True,
            "tag_name": "v0.1.0-rc.1",
            "body": "Release notes",
        }
        self.enterContext(mock_patch.dict(os.environ, {}, clear=True))
        self.enterContext(
            mock_patch(
                "scripts.cicd.github.run",
                side_effect=AssertionError("Release lookup must not call gh"),
            )
        )
        client = httpx.Client
        self.enterContext(
            mock_patch(
                "scripts.cicd.github.httpx.Client",
                side_effect=lambda **kwargs: client(
                    transport=httpx.MockTransport(self.respond), **kwargs
                ),
            )
        )

    def respond(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def test_public_release_without_token_or_gh(self):
        self.responses.append(httpx.Response(200, json=self.release))
        self.assertEqual(
            self.github.get_release("v0.1.0-rc.1"),
            {
                "isDraft": False,
                "isPrerelease": True,
                "tagName": "v0.1.0-rc.1",
                "body": "Release notes",
            },
        )
        request = self.requests[0]
        self.assertEqual(
            str(request.url),
            "https://api.github.com/repos/owner/repo/releases/tags/v0.1.0-rc.1",
        )
        self.assertNotIn("Authorization", request.headers)

    def test_environment_tokens_and_precedence(self):
        for environment, token in (
            ({"GH_TOKEN": "gh-token"}, "gh-token"),
            ({"GITHUB_TOKEN": "github-token"}, "github-token"),
            ({"GH_TOKEN": "gh-token", "GITHUB_TOKEN": "github-token"}, "gh-token"),
            ({"GH_TOKEN": "", "GITHUB_TOKEN": "github-token"}, "github-token"),
        ):
            with (
                self.subTest(environment=environment),
                mock_patch.dict(os.environ, environment, clear=True),
            ):
                self.responses.append(httpx.Response(200, json=self.release))
                self.github.get_release("v0.1.0-rc.1")
                self.assertEqual(
                    self.requests[-1].headers["Authorization"], "Bearer " + token
                )

    def test_missing_release_returns_none_when_releases_are_accessible(self):
        self.responses.extend(
            [httpx.Response(404), httpx.Response(200, json=[self.release])]
        )
        self.assertIsNone(self.github.get_release("v0.1.0-rc.2"))

    def test_draft_release_is_found_on_later_page(self):
        os.environ["GH_TOKEN"] = "test-token"
        draft = self.release | {
            "tag_name": "v0.1.0",
            "draft": True,
            "prerelease": False,
        }
        self.responses.extend(
            [
                httpx.Response(404),
                httpx.Response(
                    200,
                    json=[self.release],
                    headers={
                        "Link": '<https://api.github.com/repos/owner/repo/releases?page=2>; rel="next"'
                    },
                ),
                httpx.Response(200, json=[draft]),
            ]
        )
        result = self.github.get_release("v0.1.0")
        self.assertTrue(result["isDraft"])
        self.assertFalse(result["isPrerelease"])
        self.assertEqual(self.requests[-1].url.params["page"], "2")
        self.assertEqual(
            self.requests[-1].headers["Authorization"], "Bearer test-token"
        )

    def test_inaccessible_repository_is_not_treated_as_pending_release(self):
        self.responses.extend([httpx.Response(404), httpx.Response(404)])
        with self.assertRaisesRegex(Error, "HTTP 404.*GH_TOKEN"):
            self.github.get_release("v0.1.0-rc.1")

    def test_api_failures_are_actionable_without_exposing_token(self):
        os.environ["GH_TOKEN"] = "secret-token"
        for status in (401, 403, 429, 500):
            with self.subTest(status=status):
                self.responses.append(httpx.Response(status, text="secret-token"))
                with self.assertRaisesRegex(Error, f"HTTP {status}.*GH_TOKEN") as error:
                    self.github.get_release("v0.1.0-rc.1")
                self.assertNotIn("secret-token", str(error.exception))

    def test_network_failures_are_actionable(self):
        for failure in (httpx.ConnectError, httpx.ReadTimeout):
            with self.subTest(failure=failure):
                self.responses.append(failure("Connection failed"))
                with self.assertRaisesRegex(Error, "check the network connection"):
                    self.github.get_release("v0.1.0-rc.1")


class GitHubPublicationTests(unittest.TestCase):
    def setUp(self):
        self.github = GitHub("owner/repo")
        self.lookup = self.enterContext(
            mock_patch.object(self.github, "get_release", return_value=None)
        )
        self.run = self.enterContext(mock_patch("scripts.cicd.github.run"))

    def test_stable_release_is_created_published_and_latest(self):
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes", latest=True)
        args = self.run.call_args.args
        self.assertEqual(args[:4], ("gh", "release", "create", "v0.1.0"))
        self.assertIn("--verify-tag", args)
        self.assertIn("--draft=false", args)
        self.assertIn("--latest", args)
        self.assertNotIn("--prerelease", args)

    def test_rc_is_published_prerelease_and_never_latest(self):
        self.github.publish("v0.1.0-rc.1", {"channel": "rc"}, "Changes", latest=True)
        args = self.run.call_args.args
        self.assertIn("--draft=false", args)
        self.assertIn("--prerelease", args)
        self.assertIn("--latest=false", args)

    def test_retry_publishes_existing_stable_draft(self):
        self.lookup.return_value = {"isDraft": True, "isPrerelease": False}
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes", latest=True)
        args = self.run.call_args.args
        self.assertEqual(args[:4], ("gh", "release", "edit", "v0.1.0"))
        self.assertIn("--draft=false", args)
        self.assertIn("--latest", args)

    def test_old_stable_retry_does_not_become_latest(self):
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes", latest=False)
        self.assertIn("--latest=false", self.run.call_args.args)

    def test_published_release_is_not_rewritten(self):
        self.lookup.return_value = {"isDraft": False, "isPrerelease": False}
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes")
        self.run.assert_not_called()
