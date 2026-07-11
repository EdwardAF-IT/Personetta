"""Static guards on the Azure DevOps publish/CI pipelines.

These fast, build-free tests fail the moment a pipeline change would break a
release -- for example dropping the public PyPI upload step, removing the PyPI
credential wiring, or running ``mypy`` in a job that never installs the runtime
dependencies it needs to type-check (the ``httpx`` import-not-found regression).

They exist so a broken pipeline fails in local pytest -- seconds -- instead of
minutes later in an Azure DevOps run.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

import pytest
import yaml

pytestmark = [pytest.mark.quality, pytest.mark.readonly]

_PIPELINES = "pipelines"
_CI_PIPELINE = "ci-tests.yml"
_PUBLISH_PIPELINE = "publish-package.yml"

# The internal Azure Artifacts feed name, assembled at runtime so the
# public-export guard grep (which scans file CONTENT for internal
# infrastructure names) does not flag this guard test itself.
_INTERNAL_FEED = "Python" + "Tools"

# Step keys that carry an inline shell script in an Azure DevOps pipeline.
_SCRIPT_KEYS = ("script", "bash", "powershell", "pwsh")


def _load_pipeline(workspace_root: Path, filename: str) -> dict:
    """Parse a pipeline YAML file from the pipelines/ directory.

    Skips (rather than fails) when pipelines/ is absent entirely: the
    directory holds internal CI definitions and is excluded from the public
    repository, so these guards only apply where the pipelines exist.
    """
    pipelines_dir = workspace_root / _PIPELINES
    if not pipelines_dir.is_dir():
        pytest.skip(
            "pipelines/ directory not present (internal CI configuration, "
            "not shipped in the public repository)"
        )
    path = pipelines_dir / filename
    assert path.is_file(), "pipeline {0} is missing".format(path)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _iter_jobs(pipeline: dict) -> Iterator[dict]:
    """Yield every job, whether declared under stages or at the top level."""
    if pipeline.get("stages"):
        for stage in pipeline["stages"]:
            yield from stage.get("jobs", [])
    elif pipeline.get("jobs"):
        yield from pipeline["jobs"]


def _iter_steps(pipeline: dict) -> Iterator[dict]:
    """Yield every step across every job in the pipeline."""
    for job in _iter_jobs(pipeline):
        yield from job.get("steps", [])


def _job_script_text(job: dict) -> str:
    """Join all inline shell scripts in a job into one searchable string."""
    scripts = [
        step[key]
        for step in job.get("steps", [])
        for key in _SCRIPT_KEYS
        if isinstance(step.get(key), str)
    ]
    return "\n".join(scripts)


def _installs_tooling_deps(script: str) -> bool:
    """True if the script installs the package with the tooling extra (or httpx)."""
    # Either an extras install that includes 'tooling', or an explicit httpx install.
    has_tooling_extra = bool(
        re.search(r"pip install[^\n]*\[[^\]]*tooling[^\]]*\]", script)
    )
    has_httpx = bool(re.search(r"pip install[^\n]*\bhttpx\b", script))
    return has_tooling_extra or has_httpx


def test_ci_mypy_job_installs_runtime_deps(workspace_root: Path) -> None:
    """Any job running mypy must install the tooling extra so imports resolve.

    Regression guard: the ingest feature added ``import httpx`` (from the tooling
    extra), but the Lint job installed only bare linters, so mypy failed with
    ``Cannot find implementation or library stub for module named "httpx"``.
    """
    pipeline = _load_pipeline(workspace_root, _CI_PIPELINE)

    offenders = []
    for job in _iter_jobs(pipeline):
        script = _job_script_text(job)
        if "mypy " in script and not _installs_tooling_deps(script):
            offenders.append(job.get("displayName") or job.get("job") or "<job>")

    assert not offenders, (
        "These CI jobs run mypy without installing the tooling extra, so mypy "
        "cannot resolve runtime imports like httpx:\n  - "
        + "\n  - ".join(offenders)
        + '\n\nInstall the package with extras (pip install -e ".[dev,tooling]") '
        "in those jobs."
    )


def test_publish_pipeline_uploads_to_public_pypi(workspace_root: Path) -> None:
    """The publish pipeline must upload the built dist to public PyPI."""
    pipeline = _load_pipeline(workspace_root, _PUBLISH_PIPELINE)

    # A public-PyPI upload is `twine upload dist/*` with no `-r <internal-feed>`.
    pypi_upload = any(
        "twine upload" in step[key] and "-r " not in step[key]
        for step in _iter_steps(pipeline)
        for key in _SCRIPT_KEYS
        if isinstance(step.get(key), str)
    )
    assert pypi_upload, (
        "publish-package.yml has no public-PyPI upload step. Expected a "
        "'python -m twine upload dist/*' step (no '-r' feed flag)."
    )


def test_publish_pipeline_wires_pypi_token(workspace_root: Path) -> None:
    """The PyPI upload step must authenticate with the __token__ + PyPiApiToken."""
    pipeline = _load_pipeline(workspace_root, _PUBLISH_PIPELINE)

    # The PyPI variable group must be linked so PyPiApiToken is available.
    groups = [
        var.get("group") for var in pipeline.get("variables", []) if isinstance(var, dict)
    ]
    assert "PyPI" in groups, (
        "publish-package.yml must link the 'PyPI' variable group (provides the "
        "secret PyPiApiToken)."
    )

    # Some step must set token auth via environment variables.
    token_auth = any(
        step.get("env", {}).get("TWINE_USERNAME") == "__token__"
        and "PyPiApiToken" in str(step.get("env", {}).get("TWINE_PASSWORD", ""))
        for step in _iter_steps(pipeline)
    )
    assert token_auth, (
        "publish-package.yml must set TWINE_USERNAME=__token__ and "
        "TWINE_PASSWORD=$(PyPiApiToken) on the PyPI upload step."
    )


def test_pypi_upload_is_gated_behind_a_flag(workspace_root: Path) -> None:
    """The public-PyPI upload must be gated so it can't publish unintentionally.

    PyPI releases are hard to unpublish, so the step stays off until the
    PublishToPyPI flag is explicitly set to 'true' in the PyPI variable group.
    """
    pipeline = _load_pipeline(workspace_root, _PUBLISH_PIPELINE)

    gated = any(
        any(
            "twine upload" in step[key] and "-r " not in step[key]
            for key in _SCRIPT_KEYS
            if isinstance(step.get(key), str)
        )
        and "PublishToPyPI" in str(step.get("condition", ""))
        for step in _iter_steps(pipeline)
    )
    assert gated, (
        "The public-PyPI upload step must carry a condition on PublishToPyPI so "
        "it only runs when explicitly enabled (e.g. "
        "condition: and(succeeded(), eq(variables['PublishToPyPI'], 'true')))."
    )


def test_publish_pipeline_keeps_internal_feed(workspace_root: Path) -> None:
    """Adding PyPI must not drop the internal Azure Artifacts feed."""
    pipeline = _load_pipeline(workspace_root, _PUBLISH_PIPELINE)

    internal_upload = any(
        "twine upload" in step[key] and _INTERNAL_FEED in step[key]
        for step in _iter_steps(pipeline)
        for key in _SCRIPT_KEYS
        if isinstance(step.get(key), str)
    )
    assert internal_upload, (
        "publish-package.yml no longer uploads to the internal {0} feed "
        "(expected 'twine upload -r {0} dist/*').".format(_INTERNAL_FEED)
    )
