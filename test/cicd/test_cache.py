"""Build caches stay separate from immutable images and from other branches."""

from unittest.mock import patch
import os
import unittest

from scripts.cicd.common import Error, ROOT
from scripts.cicd.images import build_images, cache_arguments


class BuildCacheTests(unittest.TestCase):
    def environment(self, branch="develop"):
        return {
            "CICD_BUILD_CACHE": "registry",
            "BRANCH": branch,
            "REGISTRY_PREFIX": "registry.example/project",
            "IMAGE_TAG": "dev-12345678",
        }

    def test_cache_is_opt_in_for_local_and_integration_builds(self):
        self.assertEqual(cache_arguments(["runtime"], {}), [])

    def test_branch_is_required_to_avoid_shared_writer_cache(self):
        environment = self.environment()
        del environment["BRANCH"]
        with self.assertRaisesRegex(Error, "BRANCH is required"):
            cache_arguments(["runtime"], environment)

    def test_each_target_and_branch_has_its_own_cache_export(self):
        writes = []
        for branch in ("develop", "main", "release/0.2.0"):
            arguments = cache_arguments(
                ["runtime", "frontend-runtime"], self.environment(branch)
            )
            exports = [arg for arg in arguments if ".cache-to=" in arg]
            self.assertEqual(len(exports), 2)
            writes.extend(exports)
            for export in exports:
                self.assertIn("mode=max,ignore-error=true", export)
                self.assertNotIn("dev-12345678", export)
        self.assertEqual(len(set(writes)), 6)

    def test_release_reads_main_and_develop_but_only_writes_its_own_cache(self):
        args = cache_arguments(["runtime"], self.environment("release/0.2.0"))
        imports = [arg.split("ref=", 1)[1] for arg in args if ".cache-from" in arg]
        self.assertEqual(len(imports), 3)
        for branch in ("main", "develop"):
            branch_args = cache_arguments(["runtime"], self.environment(branch))
            exported = next(
                arg.split("ref=", 1)[1].split(",", 1)[0]
                for arg in branch_args
                if ".cache-to=" in arg
            )
            self.assertIn(exported, imports)
            self.assertNotEqual(exported, imports[0])

    def test_hashed_branch_names_cannot_inject_build_options(self):
        args = cache_arguments(["runtime"], self.environment("release/A,B=1/ß"))
        for arg in args:
            if "ref=" in arg:
                self.assertRegex(
                    arg.split("ref=", 1)[1].split(",", 1)[0],
                    r":buildcache-[a-f0-9]{16}$",
                )
                self.assertNotIn("A,B", arg)

    def test_one_bake_call_builds_only_requested_targets_with_cache(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("scripts.cicd.images.live") as process,
        ):
            build_images(ROOT, ["frontend-runtime"], self.environment())
        process.assert_called_once()
        arguments = process.call_args.args
        self.assertIn("--push", arguments)
        self.assertIn("--progress=plain", arguments)
        self.assertTrue(any("frontend-runtime.cache-to=" in arg for arg in arguments))
        self.assertFalse(any(arg.startswith("runtime.cache-") for arg in arguments))
