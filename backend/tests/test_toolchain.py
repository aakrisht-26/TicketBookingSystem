"""Guards on the toolchain itself.

The build is protected the same way the application is: the backend package is
installed and importable, its version has a single source of truth, it runs on
the Python version the project commits to, and the pre-commit hooks type-check
against the same dependencies as everything else.
"""

import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = BACKEND_ROOT / "pyproject.toml"
PRE_COMMIT_CONFIG = BACKEND_ROOT.parent / ".pre-commit-config.yaml"

# Type-checking the test suite needs these on top of the runtime dependencies.
_DEV_DEPENDENCIES_MYPY_NEEDS = frozenset({"httpx2", "pytest", "types-pyyaml"})


def _pyproject() -> dict[str, object]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_package_version_matches_pyproject() -> None:
    """The installed distribution is the one in this tree, at the declared version."""
    project = _pyproject()["project"]
    assert isinstance(project, dict)
    assert app.__version__ == project["version"]


def test_runs_on_python_311() -> None:
    """CLAUDE.md pins Python 3.11; a CI runner on anything else must go red."""
    assert sys.version_info[:2] == (3, 11)


def _requirement_name(requirement: str) -> str:
    """``uvicorn[standard]==0.52.4`` -> ``uvicorn``, ``httpx2>=2.11.0`` -> ``httpx2``.

    Splits on any version operator, not just ``==``, so a requirement expressed
    as a floor rather than an exact pin still resolves to its name.
    """
    return re.split(r"[<>=!~]", requirement, maxsplit=1)[0].split("[")[0]


def _mypy_hook() -> dict[str, Any]:
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text(encoding="utf-8"))
    for repo in config["repos"]:
        for hook in repo["hooks"]:
            if hook["id"] == "mypy":
                return {**hook, "_rev": repo["rev"]}
    raise AssertionError("no mypy hook in .pre-commit-config.yaml")


def test_precommit_mypy_runs_the_pinned_mypy_version() -> None:
    """A hook on a different mypy passes locally and fails in CI, or worse."""
    project = _pyproject()["project"]
    assert isinstance(project, dict)
    dev = {_requirement_name(item): item for item in project["optional-dependencies"]["dev"]}

    assert _mypy_hook()["_rev"] == "v" + dev["mypy"].split("==")[1]


def test_precommit_mypy_dependencies_match_pyproject() -> None:
    """The hook's isolated environment must be the environment mypy checks against.

    A dependency added to pyproject.toml but not here makes the hook report
    import errors that look like real findings. A version that drifts makes the
    hook and CI disagree about the same code.
    """
    project = _pyproject()["project"]
    assert isinstance(project, dict)
    runtime = set(project["dependencies"])
    dev = {
        item
        for item in project["optional-dependencies"]["dev"]
        if _requirement_name(item) in _DEV_DEPENDENCIES_MYPY_NEEDS
    }

    assert set(_mypy_hook()["additional_dependencies"]) == runtime | dev
