"""Guards on the toolchain itself.

Step 0 delivers no application behaviour, so what there is to protect is the
build: the backend package is installed and importable, its version has a
single source of truth in ``pyproject.toml``, and it runs on the Python
version the project commits to. Each assertion below fails loudly if that
stops being true.
"""

import sys
import tomllib
from pathlib import Path

import app

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


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
