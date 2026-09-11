"""Package an isolated Helm chart with immutable image references."""

from pathlib import Path
import shutil
import tempfile

import yaml

from helm.build import verify
from .common import run, write_json


def package_chart(root, destination, publication):
    """Build a temporary chart; versioned source files and dependencies stay intact."""
    verify(root / "helm")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dnk-chart-") as temporary:
        chart = Path(temporary) / "chart"
        shutil.copytree(
            root / "helm",
            chart,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        metadata = yaml.safe_load((chart / "Chart.yaml").read_text())
        metadata.update(
            version=publication["chart_version"], appVersion=publication["app_version"]
        )
        (chart / "Chart.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False))
        values = yaml.safe_load((chart / "values.yaml").read_text())
        runtime = publication["images"]["runtime"]
        frontend = publication["images"]["frontend-runtime"]
        for component in (values["backend"], *values["workers"].values()):
            component["image"].update(
                repository=runtime["repository"], tag=runtime["tag"]
            )
        values["frontend"]["image"].update(
            repository=frontend["repository"], tag=frontend["tag"]
        )
        values["global"]["deployment"]["revision"] = publication["deployment_revision"]
        (chart / "values.yaml").write_text(yaml.safe_dump(values, sort_keys=False))
        write_json(chart / "publication.json", publication)
        run("helm", "package", chart, "--destination", destination)
        config = destination / "helm-config.json"
        write_json(config, metadata)
        return destination / f'{metadata["name"]}-{metadata["version"]}.tgz', config
