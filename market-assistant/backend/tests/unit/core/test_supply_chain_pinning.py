"""H10: the backend must install from a committed lockfile with capped majors.

Config-validation tests (no runtime): CI floats and prod floats when the image
and CI install from pyproject alone. These lock the three guardrails:
  1. every dependency carries an upper bound (major cap),
  2. the Docker image installs from the frozen uv.lock,
  3. CI installs from the frozen uv.lock (not a bare editable install).
"""

import tomllib
from pathlib import Path

BACKEND = Path(__file__).parents[3]
PYPROJECT = BACKEND / "pyproject.toml"
DOCKERFILE = BACKEND / "Dockerfile"
UV_LOCK = BACKEND / "uv.lock"
CI_YML = Path(__file__).parents[5] / ".github" / "workflows" / "ci.yml"


def _all_specifiers() -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text())
    specs = list(data["project"]["dependencies"])
    for group in data["project"].get("optional-dependencies", {}).values():
        specs.extend(group)
    return specs


def test_lockfile_committed():
    assert UV_LOCK.exists(), "uv.lock must be committed so CI and prod are reproducible"


def test_every_dependency_has_an_upper_bound():
    unbounded = [s for s in _all_specifiers() if "<" not in s and "==" not in s]
    assert not unbounded, f"deps without a major cap (float on next major): {unbounded}"


def test_dockerfile_installs_from_frozen_lock():
    text = DOCKERFILE.read_text()
    assert "uv.lock" in text, "Dockerfile must COPY uv.lock into the image"
    assert "--frozen" in text, "Dockerfile must install from the frozen lock"


def test_ci_installs_from_frozen_lock():
    text = CI_YML.read_text()
    assert "--frozen" in text, "CI must install from the frozen lock"
    assert "pip install -e" not in text, "CI must not float via a bare editable install"
