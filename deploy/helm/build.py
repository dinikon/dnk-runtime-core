#!/usr/bin/env python3
"""Vendor the shared library, then optionally package the three installable charts."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
PLATFORM = ROOT / "dnk-platform"
APPLICATIONS = [
    PLATFORM / "charts" / name for name in ("dnk-control-plane", "dnk-runtime-core")
]


def prepare(helm=None):
    helm = helm or os.environ.get("HELM", "helm")
    # Local infrastructure is already vendored as source. Helm resolves only the
    # sibling library; no third-party chart repository or network is necessary.
    for chart in APPLICATIONS:
        subprocess.run(
            [helm, "dependency", "update", str(chart), "--skip-refresh"], check=True
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        help="Write dnk-platform and both standalone .tgz files here",
    )
    args = parser.parse_args()
    helm = os.environ.get("HELM", "helm")
    if not shutil.which(helm):
        parser.error("Helm is required; set HELM to its executable path")
    prepare(helm)
    if args.destination:
        args.destination.mkdir(parents=True, exist_ok=True)
        for chart in [PLATFORM, *APPLICATIONS]:
            subprocess.run(
                [helm, "package", str(chart), "--destination", str(args.destination)],
                check=True,
            )


if __name__ == "__main__":
    main()
